import logging
import os
from datetime import datetime
from config import LOG_CONFIG

class LoggerManager:
    """Singleton class to manage logger instance and configuration."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._logger = None
            self._initialized = True
    
    def setup_logger(self) -> logging.Logger:
        """
        Sets up logging configuration for both file and console output.
        Creates a logs directory if it doesn't exist.
        Uses configuration from LOG_CONFIG.
        
        Returns:
            logging.Logger: Configured logger instance
        """
        if self._logger is not None:
            return self._logger
            
        # Create logs directory if it doesn't exist
        log_dir = LOG_CONFIG['log_dir']
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Create a logger
        logger = logging.getLogger('virtual_keyboard')
        
        # Only add handlers if they haven't been added
        if not logger.handlers:
            logger.setLevel(getattr(logging, LOG_CONFIG['log_level'].upper()))

            # Create handlers
            # File handler with timestamp in filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_handler = logging.FileHandler(f'{log_dir}/virtual_keyboard_{timestamp}.log')
            file_handler.setLevel(logging.DEBUG)

            # Console handler with UTF-8 encoding for Windows compatibility
            import sys
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            # Set encoding to UTF-8 if available (for Windows Unicode support)
            if hasattr(console_handler.stream, 'reconfigure'):
                try:
                    console_handler.stream.reconfigure(encoding='utf-8')
                except Exception:
                    pass  # Fallback to default encoding

            # Create formatters and add them to handlers
            formatter = logging.Formatter(LOG_CONFIG['log_format'])
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            # Add handlers to logger
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
            # Prevent propagation to root logger
            logger.propagate = False

        self._logger = logger
        return logger
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """
        Get a logger instance. If the global logger hasn't been set up,
        it will be initialized first.
        
        Args:
            name (str, optional): Name for the logger. If None, returns the root logger.
            
        Returns:
            logging.Logger: Logger instance
        """
        if self._logger is None:
            self.setup_logger()
        
        if name:
            return logging.getLogger(f'virtual_keyboard.{name}')
        return self._logger

# Create global logger manager instance
_logger_manager = LoggerManager()

def setup_logger() -> logging.Logger:
    """Convenience function to setup the logger."""
    return _logger_manager.setup_logger()

def get_logger(name: str = None) -> logging.Logger:
    """Convenience function to get a logger instance."""
    return _logger_manager.get_logger(name)
