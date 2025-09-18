"""
Keyboard Controller Module

This module provides a singleton keyboard controller that manages keyboard input simulation
using pynput. It ensures only one instance of the keyboard controller exists throughout
the application.
"""

from typing import Optional, Union
from pynput.keyboard import Controller, Key
from .logger import get_logger

logger = get_logger(__name__)

class KeyboardController:
    """Singleton class for managing keyboard input simulation."""
    
    _instance: Optional['KeyboardController'] = None
    
    # Key mapping from string names to pynput Key enum values
    _key_mapping = {
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
        logger.info("Keyboard controller initialized")
    
    def _get_key(self, key_input: Union[str, Key]) -> Key:
        """
        Convert string key name to pynput Key enum or return Key enum directly.
        
        Args:
            key_input (Union[str, Key]): String key name or Key enum
            
        Returns:
            Key: pynput Key enum value
            
        Raises:
            ValueError: If key name is not recognized
        """
        if isinstance(key_input, Key):
            return key_input
        elif isinstance(key_input, str):
            key_name = key_input.lower().strip()
            if key_name in self._key_mapping:
                return self._key_mapping[key_name]
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
    
    def press_key(self, key: Union[str, Key]) -> None:
        """
        Simulate pressing a special key.
        
        Args:
            key (Union[str, Key]): The special key to press (string name or Key enum)
        """
        try:
            pynput_key = self._get_key(key)
            logger.debug(f"Simulating key press: {key} -> {pynput_key}")
            self._keyboard.press(pynput_key)
            logger.info(f"Successfully pressed key: {key}")
        except Exception as e:
            logger.error(f"Error while pressing key: {str(e)}")
            raise
    
    def release_key(self, key: Union[str, Key]) -> None:
        """
        Simulate releasing a special key.
        
        Args:
            key (Union[str, Key]): The special key to release (string name or Key enum)
        """
        try:
            pynput_key = self._get_key(key)
            logger.debug(f"Simulating key release: {key} -> {pynput_key}")
            self._keyboard.release(pynput_key)
            logger.info(f"Successfully released key: {key}")
        except Exception as e:
            logger.error(f"Error while releasing key: {str(e)}")
            raise 