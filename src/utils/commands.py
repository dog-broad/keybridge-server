"""
Commands Module

This module defines all supported command types and provides validation utilities
for command handling.
"""

from enum import Enum, auto
from typing import Dict, Any, List, Optional
from pynput.keyboard import Key

class CommandType(Enum):
    """Enumeration of all supported command types."""
    TYPE = "type"           # Type text
    KEY_PRESS = "key_press" # Press a single key
    KEY_RELEASE = "key_release" # Release a single key
    KEY_COMBO = "key_combo" # Press multiple keys in combination
    HOTKEY = "hotkey"      # Execute a hotkey combination

class CommandValidator:
    """Validates command structure and parameters."""
    
    @staticmethod
    def validate_command(data: Dict[str, Any]) -> None:
        """
        Validate the command structure and parameters.
        
        Args:
            data (Dict[str, Any]): Command data to validate
            
        Raises:
            ValueError: If command is invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Command must be a JSON object")
            
        if 'command' not in data:
            raise ValueError("Command must contain a 'command' field")
            
        command = data['command']
        try:
            command_type = CommandType(command)
        except ValueError:
            raise ValueError(f"Invalid command type: {command}")
            
        # Validate command-specific parameters
        if command_type == CommandType.TYPE:
            CommandValidator._validate_type_command(data)
        elif command_type == CommandType.KEY_PRESS:
            CommandValidator._validate_key_command(data)
        elif command_type == CommandType.KEY_RELEASE:
            CommandValidator._validate_key_command(data)
        elif command_type == CommandType.KEY_COMBO:
            CommandValidator._validate_key_combo_command(data)
        elif command_type == CommandType.HOTKEY:
            CommandValidator._validate_hotkey_command(data)
    
    @staticmethod
    def _validate_type_command(data: Dict[str, Any]) -> None:
        """Validate type command parameters."""
        if 'text' not in data:
            raise ValueError("'type' command requires a 'text' field")
        if not isinstance(data['text'], str):
            raise ValueError("'text' must be a string")
        if not data['text'].strip():
            raise ValueError("'text' cannot be empty")
    
    @staticmethod
    def _validate_key_command(data: Dict[str, Any]) -> None:
        """Validate key press/release command parameters."""
        if 'key' not in data:
            raise ValueError("Key command requires a 'key' field")
        if not isinstance(data['key'], str):
            raise ValueError("'key' must be a string")
        # Additional validation for special keys can be added here
    
    @staticmethod
    def _validate_key_combo_command(data: Dict[str, Any]) -> None:
        """Validate key combination command parameters."""
        if 'keys' not in data:
            raise ValueError("'key_combo' command requires a 'keys' field")
        if not isinstance(data['keys'], list):
            raise ValueError("'keys' must be a list")
        if not data['keys']:
            raise ValueError("'keys' list cannot be empty")
        for key in data['keys']:
            if not isinstance(key, str):
                raise ValueError("All keys must be strings")
    
    @staticmethod
    def _validate_hotkey_command(data: Dict[str, Any]) -> None:
        """Validate hotkey command parameters."""
        if 'keys' not in data:
            raise ValueError("'hotkey' command requires a 'keys' field")
        if not isinstance(data['keys'], list):
            raise ValueError("'keys' must be a list")
        if not data['keys']:
            raise ValueError("'keys' list cannot be empty")
        for key in data['keys']:
            if not isinstance(key, str):
                raise ValueError("All keys must be strings")

# Example command formats for documentation
COMMAND_EXAMPLES = {
    CommandType.TYPE: {
        "command": "type",
        "text": "Hello, World!"
    },
    CommandType.KEY_PRESS: {
        "command": "key_press",
        "key": "shift"
    },
    CommandType.KEY_RELEASE: {
        "command": "key_release",
        "key": "shift"
    },
    CommandType.KEY_COMBO: {
        "command": "key_combo",
        "keys": ["ctrl", "c"]
    },
    CommandType.HOTKEY: {
        "command": "hotkey",
        "keys": ["ctrl", "alt", "delete"]
    }
} 