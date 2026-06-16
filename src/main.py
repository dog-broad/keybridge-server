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
import base64
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
from utils.envelope import EnvelopeError, SeenChunks, build_ack, parse_envelope
from utils.connection_manager import ConnectionManager
from utils.qr_utils import generate_connection_qr, generate_ascii_qr
from utils.security import SecurityManager, RateLimiter
from config import SERVER_CONFIG, SECURITY_CONFIG, PERFORMANCE_CONFIG

# Initialize logger
logger = setup_logger()

# Initialize security manager (owns the pairing secret) and rate limiter.
security_manager = SecurityManager(
    enable_encryption=SECURITY_CONFIG.get('enable_encryption', True)
)
rate_limiter = RateLimiter(
    max_requests=SECURITY_CONFIG.get('rate_limit_per_minute', 300),
    window_minutes=1
)
if security_manager.enable_encryption:
    logger.info("Encryption enabled (per-session key from the QR pairing secret); rate limiting enabled")
else:
    logger.warning("Encryption disabled - running in local plaintext mode")

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

    client_id = security_manager.hash_client_identifier(client_ip)
    encryption_on = security_manager.enable_encryption
    session_key = None

    # Per-connection record of applied chunks, for idempotent client retries.
    seen_chunks = SeenChunks()

    def reply(text: str) -> str:
        """Encrypt an outbound message under the session key when encryption is on."""
        return security_manager.encrypt(text, session_key) if encryption_on else text

    try:
        session_id = await connection_manager.add_connection(websocket)

        # Handshake (plaintext): carries the per-connection salt. Both sides derive the
        # session key from it and the QR pairing secret; everything after is encrypted.
        handshake_msg = {
            "type": "handshake",
            "protocol_version": "2.0",
            "features": {
                "encryption": encryption_on,
                "compression": PERFORMANCE_CONFIG.get('enable_compression', True),
            },
            "session_id": session_id,
        }
        if encryption_on:
            salt = security_manager.new_session_salt()
            session_key = security_manager.derive_session_key(salt)
            handshake_msg["salt"] = base64.urlsafe_b64encode(salt).decode("utf-8").rstrip("=")
        await websocket.send(json.dumps(handshake_msg))

        async for message in websocket:
            try:
                # WebSocket-level ping frame.
                if isinstance(message, bytes) and message.startswith(b'\x89'):
                    await websocket.pong(message[1:] if len(message) > 1 else b'')
                    continue

                # Rate limiting. Sent as a plaintext notice the client treats as transient.
                if not rate_limiter.is_allowed(client_id):
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Rate limit exceeded. Please slow down.",
                        "code": "RATE_LIMIT_EXCEEDED",
                    }))
                    continue

                connection_manager.update_activity(websocket)

                # Decrypt. A message that does not authenticate under the session key did
                # not come from a paired client (or was tampered with) — a hard error: we
                # close the connection rather than fall back to plaintext.
                if encryption_on:
                    try:
                        decrypted_message = security_manager.decrypt(message, session_key)
                    except Exception:
                        logger.warning(f"Undecryptable message from {client_address}; closing connection")
                        await websocket.close(1008, "authentication failed")
                        return
                else:
                    decrypted_message = message

                try:
                    message_data = json.loads(decrypted_message)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON message: {e}")
                    await websocket.send(reply(json.dumps({
                        "status": "error", "message": "Invalid JSON format",
                    })))
                    continue

                # Keep-alive ping.
                if message_data.get('command') == 'ping':
                    connection_manager.extend_idle_timeout(websocket, extension_seconds=300)
                    pong_response = {
                        "status": "success",
                        "message": "pong",
                        "timestamp": message_data.get('timestamp', 0),
                        "server_time": time.time(),
                    }
                    await websocket.send(reply(json.dumps(pong_response)))
                    continue

                # Data plane: a versioned input envelope. Parse, apply, and ack.
                try:
                    envelope = parse_envelope(message_data)
                except EnvelopeError as e:
                    logger.warning(f"Rejected envelope from {client_address}: {e}")
                    if e.msg_id is not None and e.seq is not None:
                        err = build_ack(e.msg_id, e.seq, "error", str(e))
                    else:
                        err = {"status": "error", "message": str(e)}
                    await websocket.send(reply(json.dumps(err)))
                    continue

                ack = await message_handler.handle_envelope(envelope, seen_chunks)
                await websocket.send(reply(json.dumps(ack)))
                logger.debug(f"Acked {ack['id']}#{ack['seq']} -> {ack['status']}")

            except websockets.exceptions.ConnectionClosed:
                raise
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                try:
                    await websocket.send(reply(json.dumps({"status": "error", "message": str(e)})))
                except Exception:
                    pass

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
        if security_manager.enable_encryption:
            print("Encrypted connection: scan the QR to pair (the key never leaves the QR).")
        else:
            print("Local plaintext mode (no encryption).")
        
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
