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
from config import SERVER_CONFIG

# Initialize logger
logger = setup_logger()

# Initialize message handler
message_handler = MessageHandler()

# Store active connections
active_connections: Set[WebSocketServerProtocol] = set()

async def handle_connection(websocket: WebSocketServerProtocol) -> None:
    """
    Handle incoming WebSocket connections and process messages.

    Args:
        websocket: WebSocket connection object
    """
    client_address = websocket.remote_address
    logger.info(f"New connection from {client_address}")
    active_connections.add(websocket)

    try:
        async for message in websocket:
            try:
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

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Connection closed for {client_address}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        active_connections.remove(websocket)

async def shutdown(server: WebSocketServer) -> None:
    """
    Gracefully shutdown the server and close all connections.
    
    Args:
        server: WebSocket server instance
    """
    logger.info("Initiating graceful shutdown...")
    
    # Close all active connections
    for websocket in active_connections:
        try:
            await websocket.close(1000, "Server shutting down")
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
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
