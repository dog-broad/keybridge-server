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
Message Handler Module

This module handles parsing and routing of WebSocket messages, including command validation
and execution.
"""

import json
import time
import uuid
from typing import Dict, Any, Optional, Set
from .logger import get_logger
from .keyboard_controller import KeyboardController
from .commands import CommandType, CommandValidator, COMMAND_EXAMPLES

logger = get_logger(__name__)

class MessageHandler:
    """Handles parsing and routing of WebSocket messages."""
    
    def __init__(self) -> None:
        """Initialize the message handler with a keyboard controller."""
        self.keyboard = KeyboardController()
        self.pending_acknowledgments: Dict[str, Dict[str, Any]] = {}
        self.message_history: Dict[str, Dict[str, Any]] = {}
        self.max_history_size = 100
    
    def parse_message(self, message: str) -> Dict[str, Any]:
        """
        Parse a JSON message into a dictionary.
        
        Args:
            message (str): JSON message string
            
        Returns:
            Dict[str, Any]: Parsed message dictionary
            
        Raises:
            ValueError: If message is invalid JSON or missing required fields
        """
        try:
            data = json.loads(message)
            
            # Skip validation for acknowledgment messages
            if data.get('command') != 'ack':
                CommandValidator.validate_command(data)
            
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON message: {str(e)}")
            raise ValueError(f"Invalid JSON message: {str(e)}")
    
    def handle_message(self, message: str) -> Dict[str, Any]:
        """
        Handle an incoming WebSocket message.
        
        Args:
            message (str): JSON message string
            
        Returns:
            Dict[str, Any]: Response message
            
        Raises:
            ValueError: If message is invalid or command is not supported
        """
        try:
            data = self.parse_message(message)
            command = data.get('command')
            message_id = data.get('message_id')
            requires_ack = data.get('requires_ack', False)
            
            # Handle acknowledgment messages
            if command == 'ack':
                return self._handle_acknowledgment(data)
            
            # Generate message ID if not provided and acknowledgment is required
            if requires_ack and not message_id:
                message_id = str(uuid.uuid4())
                data['message_id'] = message_id
            
            # Process the command
            if command == CommandType.TYPE.value:
                response = self._handle_type_command(data)
            elif command == CommandType.KEY_PRESS.value:
                response = self._handle_key_press_command(data)
            elif command == CommandType.KEY_RELEASE.value:
                response = self._handle_key_release_command(data)
            elif command == CommandType.KEY_COMBO.value:
                response = self._handle_key_combo_command(data)
            elif command == CommandType.HOTKEY.value:
                response = self._handle_hotkey_command(data)
            elif command == "ping":
                response = self._handle_ping_command(data)
            else:
                raise ValueError(f"Unsupported command: {command}")
            
            # Add message ID to response if acknowledgment was requested
            if requires_ack and message_id:
                response['message_id'] = message_id
                response['requires_ack'] = True
                
                # Store message for potential retry - but DON'T add to pending acknowledgments yet
                # The pending acknowledgments should only be added when the message is actually sent
                self.message_history[message_id] = {
                    'command': command,
                    'data': data,
                    'response': response,
                    'timestamp': time.time()
                }
                
                # Clean up old history
                self._cleanup_message_history()
            
            return response
                
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            
            # Preserve message ID in error response
            message_id = None
            try:
                data = json.loads(message)
                message_id = data.get('message_id')
                if message_id:
                    error_response['message_id'] = message_id
            except:
                pass
                
            return error_response
    
    def _handle_type_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the 'type' command.
        
        Args:
            data (Dict[str, Any]): Command data
            
        Returns:
            Dict[str, Any]: Response message
            
        Raises:
            ValueError: If text is missing or invalid
        """
        text = data.get('text')
        if not text or not isinstance(text, str):
            raise ValueError("'type' command requires a 'text' field")
            
        # Sanitize input (basic sanitization - can be enhanced based on requirements)
        text = text.strip()
        if not text:
            raise ValueError("Text cannot be empty after sanitization")
        
        # Get optional typing delay (milliseconds between characters)
        delay_ms = data.get('delay_ms', 0)
            
        try:
            if delay_ms > 0:
                # Type with delay between characters
                import time
                for char in text:
                    self.keyboard.type_text(char)
                    time.sleep(delay_ms / 1000.0)
                logger.info(f"Successfully typed text with {delay_ms}ms delay: {text}")
            else:
                self.keyboard.type_text(text)
                logger.info(f"Successfully typed text: {text}")
            return {
                'status': 'success',
                'message': f'Successfully typed text: {text}'
            }
        except Exception as e:
            logger.error(f"Error in type command: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _handle_key_press_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the 'key_press' command."""
        try:
            self.keyboard.press_key(data['key'])
            return {
                'status': 'success',
                'message': f'Successfully pressed key: {data["key"]}'
            }
        except Exception as e:
            logger.error(f"Error in key press command: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _handle_key_release_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the 'key_release' command."""
        try:
            self.keyboard.release_key(data['key'])
            return {
                'status': 'success',
                'message': f'Successfully released key: {data["key"]}'
            }
        except Exception as e:
            logger.error(f"Error in key release command: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _handle_key_combo_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the 'key_combo' command."""
        try:
            # Press all keys in sequence
            for key in data['keys']:
                self.keyboard.press_key(key)
            # Release all keys in reverse order
            for key in reversed(data['keys']):
                self.keyboard.release_key(key)
            return {
                'status': 'success',
                'message': f'Successfully executed key combination: {data["keys"]}'
            }
        except Exception as e:
            logger.error(f"Error in key combo command: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _handle_hotkey_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the 'hotkey' command."""
        try:
            # Press all keys in sequence
            for key in data['keys']:
                self.keyboard.press_key(key)
            # Release all keys in reverse order
            for key in reversed(data['keys']):
                self.keyboard.release_key(key)
            return {
                'status': 'success',
                'message': f'Successfully executed hotkey: {data["keys"]}'
            }
        except Exception as e:
            logger.error(f"Error in hotkey command: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _handle_ping_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the 'ping' command for keep-alive."""
        try:
            timestamp = data.get('timestamp', 0)
            return {
                'status': 'success',
                'message': 'pong',
                'timestamp': timestamp,
                'server_time': time.time()
            }
        except Exception as e:
            logger.error(f"Error in ping command: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _handle_acknowledgment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle acknowledgment messages from client."""
        try:
            ack_message_id = data.get('ack_message_id')
            if not ack_message_id:
                return {
                    'status': 'error',
                    'message': 'Missing ack_message_id in acknowledgment'
                }
            
            # Remove from pending acknowledgments
            if ack_message_id in self.pending_acknowledgments:
                del self.pending_acknowledgments[ack_message_id]
                logger.info(f"[ACK] Received acknowledgment for message: {ack_message_id}")
            else:
                logger.warning(f"[ACK] Received acknowledgment for unknown message: {ack_message_id}")
            
            return {
                'status': 'success',
                'message': 'Acknowledgment received',
                'requires_ack': False  # Acknowledgment responses don't need acknowledgments
            }
        except Exception as e:
            logger.error(f"Error handling acknowledgment: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _cleanup_message_history(self) -> None:
        """Clean up old message history to prevent memory leaks."""
        if len(self.message_history) > self.max_history_size:
            # Remove oldest messages
            current_time = time.time()
            old_messages = [
                msg_id for msg_id, msg_data in self.message_history.items()
                if current_time - msg_data['timestamp'] > 300  # 5 minutes
            ]
            
            for msg_id in old_messages:
                del self.message_history[msg_id]
            
            logger.debug(f"Cleaned up {len(old_messages)} old messages from history")
    
    def get_pending_acknowledgments(self) -> Dict[str, Dict[str, Any]]:
        """Get pending acknowledgments for retry mechanism."""
        return self.pending_acknowledgments.copy()
    
    def add_pending_acknowledgment(self, message_id: str, message_data: Dict[str, Any]) -> None:
        """Add a message to pending acknowledgments."""
        self.pending_acknowledgments[message_id] = {
            'data': message_data,
            'timestamp': time.time(),
            'retry_count': 0
        }
    
    def retry_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retry a message that hasn't been acknowledged."""
        if message_id in self.message_history:
            message_data = self.message_history[message_id]
            return message_data['response']
        return None 