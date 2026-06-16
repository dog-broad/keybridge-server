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

"""
KeyBridge Server

The WebSocket host wrapped as a start/stoppable object so it can run either headless
(see main.py) or under a GUI on a background thread (see launcher.py). It owns the
security manager, rate limiter, connection manager, and message handler, and reports the
number of paired clients so a UI can show connection state.
"""

import asyncio
import base64
import json
from typing import Any, Callable, Optional

import websockets

from config import PERFORMANCE_CONFIG, SECURITY_CONFIG, SERVER_CONFIG
from utils.connection_manager import ConnectionManager
from utils.envelope import EnvelopeError, SeenChunks, build_ack, parse_envelope
from utils.logger import get_logger
from utils.message_handler import MessageHandler
from utils.qr_utils import generate_ascii_qr, generate_connection_qr, get_local_ip
from utils.security import RateLimiter, SecurityManager

logger = get_logger(__name__)


class KeyBridgeServer:
    """Owns the host's services and serves the WebSocket protocol; start/stop friendly."""

    def __init__(
        self,
        on_clients_changed: Optional[Callable[[int], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Args:
            on_clients_changed: called (on the server's loop thread) with the current
                number of paired clients whenever it changes — for a status indicator.
            on_error: called with a human-readable message if the server cannot start
                (e.g. the port is already in use).
        """
        self.host: str = SERVER_CONFIG['host']
        self.port: int = SERVER_CONFIG['port']
        self.on_clients_changed = on_clients_changed
        self.on_error = on_error

        self.security_manager = SecurityManager(
            enable_encryption=SECURITY_CONFIG.get('enable_encryption', True)
        )
        self.rate_limiter = RateLimiter(
            max_requests=SECURITY_CONFIG.get('rate_limit_per_minute', 300), window_minutes=1
        )
        self.message_handler = MessageHandler()
        self.connection_manager = ConnectionManager(
            idle_timeout=SERVER_CONFIG.get('idle_timeout', 600),
            max_connections=SERVER_CONFIG.get('max_connections', 10),
        )

        # The QR payload + saved image, computed once (pairing secret lives for this run).
        self.connection_string, self.qr_path = generate_connection_qr(self.port, self.security_manager)

        self._client_count = 0
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_server = None
        self._stop_event: Optional[asyncio.Event] = None

    # --- info for the UI / CLI --------------------------------------------------

    @property
    def encryption_enabled(self) -> bool:
        return self.security_manager.enable_encryption

    @property
    def local_ip(self) -> str:
        return get_local_ip()

    @property
    def pairing_url(self) -> str:
        return f"ws://{self.local_ip}:{self.port}"

    @property
    def client_count(self) -> int:
        return self._client_count

    def ascii_qr(self) -> str:
        return generate_ascii_qr(self.port, self.security_manager)

    def regenerate_pairing(self) -> None:
        """Rotate the pairing secret and rebuild the QR. Old codes stop working."""
        self.security_manager.regenerate_pairing_secret()
        self.connection_string, self.qr_path = generate_connection_qr(self.port, self.security_manager)

    def _set_client_count(self, count: int) -> None:
        if count != self._client_count:
            self._client_count = count
            if self.on_clients_changed:
                self.on_clients_changed(count)

    # --- lifecycle --------------------------------------------------------------

    def run(self) -> None:
        """Run the server until stop() is called (blocking). Call on a dedicated thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except KeyboardInterrupt:
            # Headless Ctrl+C: the process is exiting, so a best-effort close is enough.
            logger.info("Interrupted")
            if self._ws_server is not None:
                self._ws_server.close()
        finally:
            self._loop.close()
            self._loop = None

    def stop(self) -> None:
        """Signal the server to shut down. Safe to call from another thread."""
        loop = self._loop
        stop_event = self._stop_event
        if loop is not None and stop_event is not None:
            loop.call_soon_threadsafe(stop_event.set)

    async def _serve(self) -> None:
        self._stop_event = asyncio.Event()
        await self.connection_manager.start()
        try:
            self._ws_server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port,
                ping_interval=SERVER_CONFIG['ping_interval'],
                ping_timeout=SERVER_CONFIG['ping_timeout'],
            )
        except OSError as e:
            # Most commonly the port is already taken (another instance, or another app).
            logger.error(f"Could not start server on port {self.port}: {e}")
            await self.connection_manager.stop()
            if self.on_error:
                self.on_error(
                    f"Couldn't start: port {self.port} is already in use. "
                    f"Is KeyBridge already running?"
                )
            return
        logger.info(f"Server listening on {self.host}:{self.port}")
        try:
            await self._stop_event.wait()
        finally:
            self._ws_server.close()
            await self._ws_server.wait_closed()
            await self.connection_manager.stop()
            logger.info("Server shutdown complete")

    # --- per-connection protocol (see PROTOCOL.md) ------------------------------

    async def _handle_connection(self, websocket) -> None:
        client_address = websocket.remote_address
        client_ip = client_address[0] if client_address else "unknown"
        logger.info(f"New connection from {client_address}")

        client_id = self.security_manager.hash_client_identifier(client_ip)
        encryption_on = self.security_manager.enable_encryption
        session_key: Optional[bytes] = None
        paired = False  # counted toward client_count once the first message authenticates

        seen_chunks = SeenChunks()

        def reply(text: str) -> str:
            return self.security_manager.encrypt(text, session_key) if encryption_on else text

        try:
            session_id = await self.connection_manager.add_connection(websocket)

            handshake_msg: dict[str, Any] = {
                "type": "handshake",
                "protocol_version": "2.0",
                "features": {
                    "encryption": encryption_on,
                    "compression": PERFORMANCE_CONFIG.get('enable_compression', True),
                },
                "session_id": session_id,
            }
            if encryption_on:
                salt = self.security_manager.new_session_salt()
                session_key = self.security_manager.derive_session_key(salt)
                handshake_msg["salt"] = base64.urlsafe_b64encode(salt).decode("utf-8").rstrip("=")
            await websocket.send(json.dumps(handshake_msg))

            async for message in websocket:
                try:
                    if isinstance(message, bytes) and message.startswith(b'\x89'):
                        await websocket.pong(message[1:] if len(message) > 1 else b'')
                        continue

                    if not self.rate_limiter.is_allowed(client_id):
                        await websocket.send(json.dumps({
                            "status": "error",
                            "message": "Rate limit exceeded. Please slow down.",
                            "code": "RATE_LIMIT_EXCEEDED",
                        }))
                        continue

                    self.connection_manager.update_activity(websocket)

                    # A message that does not authenticate under the session key did not come
                    # from a paired client (or was tampered) — a hard error: close.
                    if encryption_on:
                        try:
                            decrypted_message = self.security_manager.decrypt(message, session_key)
                        except Exception:
                            logger.warning(f"Undecryptable message from {client_address}; closing connection")
                            await websocket.close(1008, "authentication failed")
                            return
                    else:
                        decrypted_message = message

                    # The first message we accept means a real, paired client is connected.
                    if not paired:
                        paired = True
                        self._set_client_count(self._client_count + 1)

                    try:
                        message_data = json.loads(decrypted_message)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON message: {e}")
                        await websocket.send(reply(json.dumps({
                            "status": "error", "message": "Invalid JSON format",
                        })))
                        continue

                    if message_data.get('command') == 'ping':
                        self.connection_manager.extend_idle_timeout(websocket, extension_seconds=300)
                        await websocket.send(reply(json.dumps({
                            "status": "success",
                            "message": "pong",
                            "timestamp": message_data.get('timestamp', 0),
                        })))
                        continue

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

                    ack = await self.message_handler.handle_envelope(envelope, seen_chunks)
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

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed for {client_address}")
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
        finally:
            if paired:
                self._set_client_count(self._client_count - 1)
            await self.connection_manager.remove_connection(websocket)
