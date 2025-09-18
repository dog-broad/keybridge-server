"""
Message Handler Module

This module handles parsing and routing of WebSocket messages, including command validation
and execution.
"""

import json
import time
from typing import Dict, Any, Optional
from .logger import get_logger
from .keyboard_controller import KeyboardController
from .commands import CommandType, CommandValidator, COMMAND_EXAMPLES

logger = get_logger(__name__)

class MessageHandler:
    """Handles parsing and routing of WebSocket messages."""
    
    def __init__(self) -> None:
        """Initialize the message handler with a keyboard controller."""
        self.keyboard = KeyboardController()
    
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
            
            if command == CommandType.TYPE.value:
                return self._handle_type_command(data)
            elif command == CommandType.KEY_PRESS.value:
                return self._handle_key_press_command(data)
            elif command == CommandType.KEY_RELEASE.value:
                return self._handle_key_release_command(data)
            elif command == CommandType.KEY_COMBO.value:
                return self._handle_key_combo_command(data)
            elif command == CommandType.HOTKEY.value:
                return self._handle_hotkey_command(data)
            elif command == "ping":
                return self._handle_ping_command(data)
            else:
                raise ValueError(f"Unsupported command: {command}")
                
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
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
            
        try:
            self.keyboard.type_text(text)
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