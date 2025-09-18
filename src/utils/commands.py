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

# Key mapping from string names to pynput Key enum values (same as in KeyboardController)
SUPPORTED_KEYS = {
    # Navigation keys
    'backspace': Key.backspace,
    'tab': Key.tab,
    'enter': Key.enter,
    'shift': Key.shift,
    'ctrl': Key.ctrl,
    'alt': Key.alt,
    'space': Key.space,
    'esc': Key.esc,
    'escape': Key.esc,
    
    # Arrow keys
    'up': Key.up,
    'down': Key.down,
    'left': Key.left,
    'right': Key.right,
    
    # Function keys
    'f1': Key.f1,
    'f2': Key.f2,
    'f3': Key.f3,
    'f4': Key.f4,
    'f5': Key.f5,
    'f6': Key.f6,
    'f7': Key.f7,
    'f8': Key.f8,
    'f9': Key.f9,
    'f10': Key.f10,
    'f11': Key.f11,
    'f12': Key.f12,
    
    # Special keys
    'home': Key.home,
    'end': Key.end,
    'page_up': Key.page_up,
    'page_down': Key.page_down,
    'insert': Key.insert,
    'delete': Key.delete,
    
    # Modifier keys
    'cmd': Key.cmd,
    'command': Key.cmd,
    'windows': Key.cmd,
    'win': Key.cmd,
    
    # Media keys
    'media_play_pause': Key.media_play_pause,
    'media_volume_up': Key.media_volume_up,
    'media_volume_down': Key.media_volume_down,
    'media_volume_mute': Key.media_volume_mute,
    'media_next': Key.media_next,
    'media_previous': Key.media_previous,
    
    # Num lock and scroll lock
    'num_lock': Key.num_lock,
    'scroll_lock': Key.scroll_lock,
    'caps_lock': Key.caps_lock,
    
    # Print screen
    'print_screen': Key.print_screen,
    'prtsc': Key.print_screen,
    'prtscr': Key.print_screen,
    
    # Pause/Break
    'pause': Key.pause,
    'break': Key.pause,
    
    # Menu key
    'menu': Key.menu,
    'apps': Key.menu,
}

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
        
        # Validate that the key is supported
        key_name = data['key'].lower().strip()
        if key_name not in SUPPORTED_KEYS:
            supported_keys_list = ', '.join(sorted(SUPPORTED_KEYS.keys()))
            raise ValueError(f"Unsupported key: '{data['key']}'. Supported keys: {supported_keys_list}")
    
    @staticmethod
    def _validate_key_combo_command(data: Dict[str, Any]) -> None:
        """Validate key combination command parameters."""
        if 'keys' not in data:
            raise ValueError("'key_combo' command requires a 'keys' field")
        if not isinstance(data['keys'], list):
            raise ValueError("'keys' must be a list")
        if not data['keys']:
            raise ValueError("'keys' list cannot be empty")
        
        # Validate each key in the list
        for i, key in enumerate(data['keys']):
            if not isinstance(key, str):
                raise ValueError(f"All keys must be strings. Key at index {i} is {type(key)}")
            
            key_name = key.lower().strip()
            if key_name not in SUPPORTED_KEYS:
                supported_keys_list = ', '.join(sorted(SUPPORTED_KEYS.keys()))
                raise ValueError(f"Unsupported key at index {i}: '{key}'. Supported keys: {supported_keys_list}")
    
    @staticmethod
    def _validate_hotkey_command(data: Dict[str, Any]) -> None:
        """Validate hotkey command parameters."""
        if 'keys' not in data:
            raise ValueError("'hotkey' command requires a 'keys' field")
        if not isinstance(data['keys'], list):
            raise ValueError("'keys' must be a list")
        if not data['keys']:
            raise ValueError("'keys' list cannot be empty")
        
        # Validate each key in the list
        for i, key in enumerate(data['keys']):
            if not isinstance(key, str):
                raise ValueError(f"All keys must be strings. Key at index {i} is {type(key)}")
            
            key_name = key.lower().strip()
            if key_name not in SUPPORTED_KEYS:
                supported_keys_list = ', '.join(sorted(SUPPORTED_KEYS.keys()))
                raise ValueError(f"Unsupported key at index {i}: '{key}'. Supported keys: {supported_keys_list}")

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