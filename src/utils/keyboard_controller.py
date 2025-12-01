"""
Keyboard Controller Module

This module provides a singleton keyboard controller that manages keyboard input simulation
using pynput. It ensures only one instance of the keyboard controller exists throughout
the application. Handles cross-platform differences between Windows, Mac, and Linux.
"""

import platform
from typing import Optional, Union, Any
from pynput.keyboard import Controller, Key
from .logger import get_logger

logger = get_logger(__name__)

# Detect operating system
IS_MACOS = platform.system() == 'Darwin'
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

class KeyboardController:
    """Singleton class for managing keyboard input simulation."""
    
    _instance: Optional['KeyboardController'] = None
    
    # Key mapping from string names to pynput Key enum values
    _key_mapping = {
        # Navigation keys
        'backspace': Key.backspace,
        'tab': Key.tab,
        'enter': Key.enter,
        'return': Key.enter,  # Mac alias
        'shift': Key.shift,
        'ctrl': Key.ctrl,
        'control': Key.ctrl,  # Mac alias
        'alt': Key.alt,
        'option': Key.alt,    # Mac alias - Option key is Alt
        'opt': Key.alt,       # Mac alias
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
        'delete': Key.delete,
        
        # Modifier keys - Command/Windows/Super
        'cmd': Key.cmd,
        'command': Key.cmd,
        'windows': Key.cmd,
        'win': Key.cmd,
        'super': Key.cmd,     # Linux alias
        'meta': Key.cmd,      # Generic alias
        
        # Media keys
        'media_play_pause': Key.media_play_pause,
        'media_volume_up': Key.media_volume_up,
        'media_volume_down': Key.media_volume_down,
        'media_volume_mute': Key.media_volume_mute,
        'media_next': Key.media_next,
        'media_previous': Key.media_previous,
        
        # Caps lock (works on all platforms)
        'caps_lock': Key.caps_lock,
        'capslock': Key.caps_lock,
    }
    
    # Keys that may not exist on all platforms - handle gracefully
    _platform_specific_keys = {}
    
    # Windows/Linux specific keys (may not work on Mac)
    if not IS_MACOS:
        _platform_specific_keys.update({
            'insert': Key.insert,
            'ins': Key.insert,
            'num_lock': Key.num_lock,
            'numlock': Key.num_lock,
            'scroll_lock': Key.scroll_lock,
            'scrolllock': Key.scroll_lock,
            'print_screen': Key.print_screen,
            'prtsc': Key.print_screen,
            'prtscr': Key.print_screen,
            'printscreen': Key.print_screen,
            'pause': Key.pause,
            'break': Key.pause,
            'menu': Key.menu,
            'apps': Key.menu,
        })
    
    # Merge platform-specific keys into main mapping
    _key_mapping.update(_platform_specific_keys)
    
    # Keys that don't exist on Mac but we should handle gracefully
    _mac_unsupported_keys = {
        'insert', 'ins', 'num_lock', 'numlock', 'scroll_lock', 'scrolllock',
        'print_screen', 'prtsc', 'prtscr', 'printscreen', 'pause', 'break',
        'menu', 'apps'
    }
    
    def __new__(cls) -> 'KeyboardController':
        """Ensure only one instance of KeyboardController exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the keyboard controller if not already initialized."""
        if self._initialized:
            return
            
        self._keyboard = Controller()
        self._initialized = True
        
        os_name = "macOS" if IS_MACOS else ("Windows" if IS_WINDOWS else "Linux")
        logger.info(f"Keyboard controller initialized for {os_name}")
        
        if IS_MACOS:
            logger.info("Mac detected: Some Windows-specific keys (Insert, PrintScreen, etc.) will be ignored")
    
    def _get_key(self, key_input: Union[str, Key]):
        """
        Convert string key name to pynput Key enum, character, or return Key enum directly.
        Handles platform-specific differences gracefully.
        
        Args:
            key_input (Union[str, Key]): String key name or Key enum
            
        Returns:
            Key, str, or None: pynput Key enum value, single character, or None if unsupported
            
        Raises:
            ValueError: If key name is not recognized
        """
        if isinstance(key_input, Key):
            return key_input
        elif isinstance(key_input, str):
            key_name = key_input.lower().strip()
            
            # Check if this is a Mac-unsupported key on Mac
            if IS_MACOS and key_name in self._mac_unsupported_keys:
                logger.warning(f"Key '{key_name}' is not available on macOS - skipping")
                return None
            
            if key_name in self._key_mapping:
                return self._key_mapping[key_name]
            elif len(key_name) == 1:
                # Single character keys (a-z, 0-9, symbols)
                return key_name
            else:
                raise ValueError(f"Unrecognized key name: {key_input}")
        else:
            raise ValueError(f"Invalid key type: {type(key_input)}. Expected str or Key enum")
    
    def type_text(self, text: str) -> None:
        """
        Simulate typing the given text.
        
        Args:
            text (str): The text to type
            
        Raises:
            ValueError: If text is None or empty
        """
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")
            
        try:
            logger.debug(f"Simulating typing: {text}")
            self._keyboard.type(text)
            logger.info(f"Successfully typed text: {text}")
        except Exception as e:
            logger.error(f"Error while typing text: {str(e)}")
            raise
    
    def press_key(self, key: Union[str, Key]) -> bool:
        """
        Simulate pressing a special key.
        
        Args:
            key (Union[str, Key]): The special key to press (string name or Key enum)
            
        Returns:
            bool: True if key was pressed, False if key is unsupported on this platform
        """
        try:
            pynput_key = self._get_key(key)
            
            # Handle unsupported keys gracefully
            if pynput_key is None:
                logger.debug(f"Skipping unsupported key: {key}")
                return False
            
            logger.debug(f"Simulating key press: {key} -> {pynput_key}")
            self._keyboard.press(pynput_key)
            logger.info(f"Successfully pressed key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error while pressing key: {str(e)}")
            raise
    
    def release_key(self, key: Union[str, Key]) -> bool:
        """
        Simulate releasing a special key.
        
        Args:
            key (Union[str, Key]): The special key to release (string name or Key enum)
            
        Returns:
            bool: True if key was released, False if key is unsupported on this platform
        """
        try:
            pynput_key = self._get_key(key)
            
            # Handle unsupported keys gracefully
            if pynput_key is None:
                logger.debug(f"Skipping unsupported key: {key}")
                return False
                
            logger.debug(f"Simulating key release: {key} -> {pynput_key}")
            self._keyboard.release(pynput_key)
            logger.info(f"Successfully released key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error while releasing key: {str(e)}")
            raise 