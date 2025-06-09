import asyncio
import json
import signal
import sys
import traceback
from typing import Any, Dict, Set
import websockets
from websockets.server import WebSocketServer
from websockets.legacy.server import WebSocketServerProtocol
from utils.logger import setup_logger
from utils.message_handler import MessageHandler
from utils.connection_manager import ConnectionManager
from config import SERVER_CONFIG

# Initialize logger
logger = setup_logger()

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
    logger.info(f"New connection from {client_address}")
    
    try:
        # Add connection to manager and get session ID
        session_id = await connection_manager.add_connection(websocket)
        
        async for message in websocket:
            try:
                # Update last activity timestamp
                connection_manager.update_activity(websocket)
                
                # Handle ping messages
                if isinstance(message, bytes) and message.startswith(b'\x89'):  # WebSocket ping frame
                    logger.debug(f"Received ping from {client_address}")
                    await websocket.pong(message[1:] if len(message) > 1 else b'')
                    continue
                
                # Process the message using our message handler
                response = message_handler.handle_message(message)
                logger.debug(f"Message response: {response}")

                # Send the response back to the client
                await websocket.send(json.dumps(response))

            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                await websocket.send(json.dumps({
                    "status": "error",
                    "message": str(e)
                }))

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
