"""
Keyboard Controller Module

This module provides a singleton keyboard controller that manages keyboard input simulation
using pynput. It ensures only one instance of the keyboard controller exists throughout
the application.
"""

from typing import Optional
from pynput.keyboard import Controller, Key
from .logger import get_logger

logger = get_logger(__name__)

class KeyboardController:
    """Singleton class for managing keyboard input simulation."""
    
    _instance: Optional['KeyboardController'] = None
    
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
    
    def press_key(self, key: Key) -> None:
        """
        Simulate pressing a special key.
        
        Args:
            key (Key): The special key to press
        """
        try:
            logger.debug(f"Simulating key press: {key}")
            self._keyboard.press(key)
            logger.info(f"Successfully pressed key: {key}")
        except Exception as e:
            logger.error(f"Error while pressing key: {str(e)}")
            raise
    
    def release_key(self, key: Key) -> None:
        """
        Simulate releasing a special key.
        
        Args:
            key (Key): The special key to release
        """
        try:
            logger.debug(f"Simulating key release: {key}")
            self._keyboard.release(key)
            logger.info(f"Successfully released key: {key}")
        except Exception as e:
            logger.error(f"Error while releasing key: {str(e)}")
            raise 