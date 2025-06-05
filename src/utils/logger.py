import logging
import os
from datetime import datetime
from config import LOG_CONFIG

def setup_logger():
    """
    Sets up logging configuration for both file and console output.
    Creates a logs directory if it doesn't exist.
    Uses configuration from LOG_CONFIG.
    """
    # Create logs directory if it doesn't exist
    log_dir = LOG_CONFIG['log_dir']
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create a logger
    logger = logging.getLogger('virtual_keyboard')
    logger.setLevel(getattr(logging, LOG_CONFIG['log_level'].upper()))

    # Create handlers
    # File handler with timestamp in filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = logging.FileHandler(f'{log_dir}/virtual_keyboard_{timestamp}.log')
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatters and add them to handlers
    formatter = logging.Formatter(LOG_CONFIG['log_format'])
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
