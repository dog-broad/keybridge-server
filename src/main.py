import asyncio
import json
from typing import Any, Dict
import websockets
from websockets.server import WebSocketServerProtocol
from pynput.keyboard import Controller, Key # type: ignore
from utils.logger import setup_logger

# Initialize logger
logger = setup_logger()

# Initialize keyboard controller
keyboard = Controller()

async def handle_connection(websocket: WebSocketServerProtocol) -> None:
    """
    Handle incoming WebSocket connections and process messages.

    Args:
        websocket: WebSocket connection object
    """
    client_address = websocket.remote_address
    logger.info(f"New connection from {client_address}")

    try:
        async for message in websocket:
            try:
                # Parse the message as JSON
                data: Dict[str, Any] = json.loads(message)

                # Validate message structure
                if not isinstance(data, dict) or 'type' not in data or 'value' not in data:
                    logger.error(f"Invalid message format: {message}")
                    continue

                # Process the message based on type
                if data['type'] == 'key':
                    logger.debug(f"Received key: {data['value']}")
                    keyboard.type(data['value'])
                else:
                    logger.warning(f"Unknown message type: {data['type']}")

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {message}")
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Connection closed for {client_address}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

async def main() -> None:
    """
    Main entry point for the WebSocket server.
    """
    host = "localhost"
    port = 8080

    logger.info(f"Starting WebSocket server on {host}:{port}")

    # Create server
    server = await websockets.serve(handle_connection, host, port)
    
    try:
        logger.info("Server is running. Press Ctrl+C to stop.")
        await asyncio.Future()  # run forever
    except asyncio.CancelledError:
        logger.info("Shutting down server...")
        server.close()
        await server.wait_closed()
        logger.info("Server shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
    finally:
        # No need to manually close the event loop as asyncio.run() handles this
        logger.info("Cleanup complete.")
