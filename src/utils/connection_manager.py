"""
Connection Manager Module

This module handles WebSocket connection tracking, session management,
and connection status notifications.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Set, Optional, List, Any
from websockets.legacy.server import WebSocketServerProtocol
from .logger import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    """Manages WebSocket connections and sessions."""
    
    def __init__(self, idle_timeout: int = 300, max_connections: int = 10) -> None:
        """
        Initialize the connection manager.
        
        Args:
            idle_timeout (int): Timeout in seconds for idle connections (default: 5 minutes)
            max_connections (int): Maximum number of concurrent connections allowed
        """
        self.active_connections: Set[WebSocketServerProtocol] = set()
        self.session_ids: Dict[WebSocketServerProtocol, str] = {}
        self.last_activity: Dict[WebSocketServerProtocol, float] = {}
        self.connection_history: List[Dict[str, Any]] = []  # Track connection history
        self.idle_timeout = idle_timeout
        self.max_connections = max_connections
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the connection manager and cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_connections())
        logger.info("Connection manager started")
    
    async def stop(self) -> None:
        """Stop the connection manager and cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Connection manager stopped")
    
    def _is_connection_allowed(self, client_address: str) -> bool:
        """
        Check if a new connection is allowed based on limits and history.
        
        Args:
            client_address: Client's IP address
            
        Returns:
            bool: True if connection is allowed, False otherwise
        """
        # Check if we've reached the maximum connection limit
        if len(self.active_connections) >= self.max_connections:
            logger.warning(f"Connection limit reached ({self.max_connections})")
            return False
            
        # Check for rapid reconnection attempts
        recent_connections = [
            conn for conn in self.connection_history
            if conn['address'] == client_address
            and time.time() - conn['timestamp'] < 60  # Within last minute
        ]
        
        if len(recent_connections) >= 5:  # More than 5 connections in a minute
            logger.warning(f"Too many rapid reconnections from {client_address}")
            return False
            
        return True
    
    async def add_connection(self, websocket: WebSocketServerProtocol) -> str:
        """
        Add a new connection and generate a session ID.
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            str: Generated session ID
            
        Raises:
            ConnectionRefusedError: If connection is not allowed
        """
        client_address = websocket.remote_address[0]
        
        # Log connection details including headers
        try:
            headers = {}
            if hasattr(websocket, 'request') and websocket.request is not None:
                headers = dict(websocket.request.headers)
            logger.info(f"New connection attempt from IP: {client_address}")
            logger.debug(f"Connection headers: {json.dumps(headers, indent=2)}")
        except Exception as e:
            logger.warning(f"Could not access request headers: {str(e)}")
            headers = {}
        
        if not self._is_connection_allowed(client_address):
            raise ConnectionRefusedError("Connection limit reached or too many rapid reconnections")
        
        session_id = str(uuid.uuid4())
        self.active_connections.add(websocket)
        self.session_ids[websocket] = session_id
        self.last_activity[websocket] = time.time()
        
        # Record connection in history with additional details
        connection_record = {
            'address': client_address,
            'session_id': session_id,
            'timestamp': time.time(),
            'headers': headers
        }
        self.connection_history.append(connection_record)
        
        # Clean up old history entries (older than 1 hour)
        current_time = time.time()
        self.connection_history = [
            conn for conn in self.connection_history
            if current_time - conn['timestamp'] < 3600  # 1 hour
        ]
        
        # Send connection status to client
        await self._send_connection_status(websocket, "connected", session_id)
        logger.info(f"New connection established - Session ID: {session_id}")
        
        return session_id
    
    async def remove_connection(self, websocket: WebSocketServerProtocol) -> None:
        """
        Remove a connection and clean up associated data.
        
        Args:
            websocket: WebSocket connection object
        """
        if websocket in self.active_connections:
            session_id = self.session_ids.get(websocket)
            self.active_connections.remove(websocket)
            self.session_ids.pop(websocket, None)
            self.last_activity.pop(websocket, None)
            
            logger.info(f"Connection removed - Session ID: {session_id}")
    
    def update_activity(self, websocket: WebSocketServerProtocol) -> None:
        """
        Update the last activity timestamp for a connection.
        
        Args:
            websocket: WebSocket connection object
        """
        if websocket in self.active_connections:
            self.last_activity[websocket] = time.time()
            logger.debug(f"Updated activity for connection - Session ID: {self.session_ids.get(websocket)}")
    
    def extend_idle_timeout(self, websocket: WebSocketServerProtocol, extension_seconds: int = 300) -> None:
        """
        Extend the idle timeout for a connection (e.g., when ping is received).
        
        Args:
            websocket: WebSocket connection object
            extension_seconds (int): Number of seconds to extend the timeout
        """
        if websocket in self.active_connections:
            current_time = time.time()
            self.last_activity[websocket] = current_time + extension_seconds
            session_id = self.session_ids.get(websocket)
            logger.debug(f"Extended idle timeout for connection - Session ID: {session_id}, Extended by {extension_seconds}s")
    
    async def _send_connection_status(self, websocket: WebSocketServerProtocol, status: str, session_id: str) -> None:
        """
        Send connection status to client.
        
        Args:
            websocket: WebSocket connection object
            status: Connection status ("connected" or "disconnected")
            session_id: Session ID
        """
        try:
            await websocket.send(json.dumps({
                "type": "connection_status",
                "status": status,
                "session_id": session_id
            }))
        except Exception as e:
            logger.error(f"Error sending connection status: {str(e)}")
    
    async def _cleanup_idle_connections(self) -> None:
        """Periodically check and cleanup idle connections."""
        while True:
            try:
                current_time = time.time()
                to_remove = set()
                
                for websocket in self.active_connections:
                    last_active = self.last_activity.get(websocket, 0)
                    if current_time - last_active > self.idle_timeout:
                        to_remove.add(websocket)
                
                for websocket in to_remove:
                    session_id = self.session_ids.get(websocket)
                    logger.info(f"Closing idle connection - Session ID: {session_id}")
                    await self.remove_connection(websocket)
                    try:
                        await websocket.close(1000, "Connection idle timeout")
                    except Exception as e:
                        logger.error(f"Error closing idle connection: {str(e)}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying 