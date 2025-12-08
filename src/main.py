# Copyright 2025 Rushyendra Guntupalli (dog-broad) and Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import json
import signal
import sys
import time
import traceback
from typing import Any, Dict, Set
import websockets
from websockets.server import WebSocketServer
from websockets.legacy.server import WebSocketServerProtocol
from utils.logger import setup_logger
from utils.message_handler import MessageHandler
from utils.connection_manager import ConnectionManager
from utils.qr_utils import generate_connection_qr, generate_ascii_qr
from utils.security import SecurityManager, RateLimiter
from config import SERVER_CONFIG, SECURITY_CONFIG, PERFORMANCE_CONFIG

# Initialize logger
logger = setup_logger()

# Initialize security manager
security_manager = None
rate_limiter = None
if SECURITY_CONFIG.get('enable_authentication', True):
    security_manager = SecurityManager(
        secret_key=SECURITY_CONFIG.get('secret_key', 'default-secret-key'),
        enable_encryption=SECURITY_CONFIG.get('enable_encryption', True)
    )
    rate_limiter = RateLimiter(
        max_requests=SECURITY_CONFIG.get('rate_limit_per_minute', 100),
        window_minutes=1
    )
    security_features = ["Authentication", "Rate limiting"]
    if SECURITY_CONFIG.get('enable_encryption', True):
        security_features.append("Encryption")
    logger.info(f"Security features enabled: {', '.join(security_features)}")
else:
    logger.warning("Security features disabled - running in legacy mode")

# Initialize message handler and connection manager
message_handler = MessageHandler()
connection_manager = ConnectionManager(
    idle_timeout=SERVER_CONFIG.get('idle_timeout', 60),
    max_connections=SERVER_CONFIG.get('max_connections', 10)
)

async def handle_connection(websocket: WebSocketServerProtocol) -> None:
    """
    Handle incoming WebSocket connections and process messages.

    Args:
        websocket: WebSocket connection object
    """
    client_address = websocket.remote_address
    client_ip = client_address[0] if client_address else "unknown"
    logger.info(f"New connection from {client_address}")
    
    # Track authentication state
    is_authenticated = not SECURITY_CONFIG.get('enable_authentication', True)
    auth_attempts = 0
    client_id = security_manager.hash_client_identifier(client_ip) if security_manager else client_ip
    
    try:
        # Add connection to manager and get session ID
        session_id = await connection_manager.add_connection(websocket)
        
        # Send initial handshake message
        handshake_msg = {
            "type": "handshake",
            "protocol_version": "2.0",
            "features": {
                "authentication": SECURITY_CONFIG.get('enable_authentication', True),
                "encryption": SECURITY_CONFIG.get('enable_encryption', True),
                "compression": PERFORMANCE_CONFIG.get('enable_compression', True)
            },
            "session_id": session_id
        }
        await websocket.send(json.dumps(handshake_msg))
        
        async for message in websocket:
            try:
                # Rate limiting check
                if rate_limiter and not rate_limiter.is_allowed(client_id):
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Rate limit exceeded. Please slow down.",
                        "code": "RATE_LIMIT_EXCEEDED"
                    }))
                    continue
                
                # Update last activity timestamp
                connection_manager.update_activity(websocket)
                
                # Handle ping messages
                if isinstance(message, bytes) and message.startswith(b'\x89'):  # WebSocket ping frame
                    logger.debug(f"Received ping from {client_address}")
                    await websocket.pong(message[1:] if len(message) > 1 else b'')
                    continue
                
                # Decrypt message if encryption is enabled and client is authenticated
                if security_manager and security_manager.enable_encryption and is_authenticated:
                    # Strip newlines and whitespace that may be added during WebSocket transmission
                    clean_message = message.strip().replace('\n', '').replace('\r', '')
                    decrypted_message = security_manager.decrypt_message(clean_message)
                    if decrypted_message is None:
                        # Try processing as plain text (backward compatibility)
                        logger.debug("Decryption failed, falling back to plain text")
                        decrypted_message = message
                else:
                    decrypted_message = message
                
                # Parse message
                try:
                    message_data = json.loads(decrypted_message)
                    logger.debug(f"Successfully parsed message: {message_data}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON message: {decrypted_message[:100]}... Error: {e}", exc_info=True)
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Invalid JSON format"
                    }))
                    continue
                
                # Handle authentication
                if not is_authenticated and message_data.get('command') == 'authenticate':
                    auth_attempts += 1
                    if auth_attempts > SECURITY_CONFIG.get('max_auth_attempts', 3):
                        logger.warning(f"Too many authentication attempts from {client_address}")
                        await websocket.close(1008, "Too many authentication attempts")
                        return
                    
                    token = message_data.get('token')
                    
                    if security_manager and security_manager.validate_connection_token(token):
                        is_authenticated = True
                        response = {
                            'status': 'success',
                            'message': 'Authentication successful',
                            'session_id': session_id
                        }
                        logger.info(f"Client {client_address} authenticated successfully")
                    else:
                        response = {
                            'status': 'error',
                            'message': 'Authentication failed',
                            'attempts_remaining': SECURITY_CONFIG.get('max_auth_attempts', 3) - auth_attempts
                        }
                        logger.warning(f"Authentication failed for {client_address}")
                    
                    # Authentication response sent as plain text
                    response_json = json.dumps(response)
                    await websocket.send(response_json)
                    continue
                
                # Reject unauthenticated commands (except ping)
                if not is_authenticated and message_data.get('command') != 'ping':
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Authentication required",
                        "code": "AUTHENTICATION_REQUIRED"
                    }))
                    continue
                
                # Handle custom ping command for keep-alive
                if message_data.get('command') == 'ping':
                    logger.debug(f"Received keep-alive ping from {client_address}")
                    # Extend the idle timeout for this connection
                    connection_manager.extend_idle_timeout(websocket, extension_seconds=300)
                    # Send pong response
                    pong_response = {
                        'status': 'success',
                        'message': 'pong',
                        'timestamp': message_data.get('timestamp', 0),
                        'server_time': time.time()
                    }
                    
                    response_json = json.dumps(pong_response)
                    if security_manager and security_manager.enable_encryption and is_authenticated:
                        response_json = security_manager.encrypt_message(response_json)
                    
                    await websocket.send(response_json)
                    continue
                
                # Process the message using our message handler
                response = message_handler.handle_message(decrypted_message)
                logger.debug(f"Message response: {response}")

                # Check if this response requires acknowledgment tracking
                message_id = response.get('message_id')
                requires_ack = response.get('requires_ack', False)
                
                if requires_ack and message_id:
                    # Add to pending acknowledgments ONLY when we're about to send the response
                    message_handler.add_pending_acknowledgment(message_id, response)
                    logger.debug(f"Added message {message_id} to pending acknowledgments")

                # Encrypt response if needed (only after authentication)
                response_json = json.dumps(response)
                if security_manager and security_manager.enable_encryption and is_authenticated:
                    response_json = security_manager.encrypt_message(response_json)

                # Send the response back to the client
                await websocket.send(response_json)
                logger.debug(f"Sent response: {response_json[:100]}..." if len(response_json) > 100 else f"Sent response: {response_json}")

            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                error_response = json.dumps({
                    "status": "error",
                    "message": str(e)
                })
                
                # Encrypt error response if needed
                if security_manager and security_manager.enable_encryption:
                    error_response = security_manager.encrypt_message(error_response)
                
                await websocket.send(error_response)

    except ConnectionRefusedError as e:
        logger.warning(f"Connection refused for {client_address}: {str(e)}")
        try:
            await websocket.close(1008, str(e))  # Policy Violation
        except Exception:
            pass
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Connection closed for {client_address}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        await connection_manager.remove_connection(websocket)

async def shutdown(server: WebSocketServer) -> None:
    """
    Gracefully shutdown the server and close all connections.
    
    Args:
        server: WebSocket server instance
    """
    logger.info("Initiating graceful shutdown...")
    
    # Stop the connection manager
    await connection_manager.stop()
    
    # Close the server
    server.close()
    await server.wait_closed()
    logger.info("Server shutdown complete")

async def main() -> None:
    """
    Main entry point for the WebSocket server.
    """
    host = SERVER_CONFIG['host']
    port = SERVER_CONFIG['port']

    logger.info(f"Starting WebSocket server on {host}:{port}")

    try:
        # Generate QR code for connection
        connection_string, qr_path = generate_connection_qr(port, security_manager)
        logger.info(f"Generated QR code for connection data: {len(connection_string)} characters")
        logger.info(f"QR code saved to: {qr_path}")
        
        # Display ASCII QR code in terminal
        ascii_qr = generate_ascii_qr(port, security_manager)
        print("\nASCII QR Code:")
        print(ascii_qr)
        print(f"Connection data length: {len(connection_string)} characters")
        if security_manager:
            print("🔒 Secure connection with authentication enabled")
        else:
            print("⚠️  Legacy connection mode (no authentication)")
        
        # Start the connection manager
        await connection_manager.start()
        
        # Create server with ping settings
        server = await websockets.serve(
            handle_connection,
            host,
            port,
            ping_interval=SERVER_CONFIG['ping_interval'],
            ping_timeout=SERVER_CONFIG['ping_timeout']
        )

        # Set up signal handlers for Unix-like systems
        if sys.platform != 'win32':
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda: asyncio.create_task(shutdown(server))
                )

        logger.info("Server is running. Press Ctrl+C to stop.")
        await asyncio.Future()  # run forever
    except asyncio.CancelledError:
        await shutdown(server)
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("Cleanup complete.")
