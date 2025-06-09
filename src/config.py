"""
Configuration settings for the virtual keyboard server.
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Server configuration
SERVER_CONFIG: Dict[str, Any] = {
    'host': os.getenv('SERVER_HOST', '0.0.0.0'),  # Listen on all available network interfaces
    'port': int(os.getenv('SERVER_PORT', 8765)),  # Default WebSocket port
    'allowed_origins': os.getenv('ALLOWED_ORIGINS', '*').split(','),
    'ping_interval': int(os.getenv('PING_INTERVAL', 20)),  # Send ping every 20 seconds
    'ping_timeout': int(os.getenv('PING_TIMEOUT', 20)),    # Wait 20 seconds for pong response
    'idle_timeout': int(os.getenv('IDLE_TIMEOUT', 60)),    # Close idle connections after 1 minute
    'max_connections': int(os.getenv('MAX_CONNECTIONS', 10)),  # Maximum concurrent connections
}

# Logging configuration
LOG_CONFIG: Dict[str, Any] = {
    'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_dir': 'logs',
} 