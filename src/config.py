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
    'idle_timeout': int(os.getenv('IDLE_TIMEOUT', 600)),   # Close idle connections after 10 minutes
    'max_connections': int(os.getenv('MAX_CONNECTIONS', 10)),  # Maximum concurrent connections
}

# Security configuration
SECURITY_CONFIG: Dict[str, Any] = {
    'enable_authentication': os.getenv('ENABLE_AUTH', 'true').lower() == 'true',
    'token_expiry_minutes': int(os.getenv('TOKEN_EXPIRY', 60)),  # QR tokens expire after 1 hour
    'max_auth_attempts': int(os.getenv('MAX_AUTH_ATTEMPTS', 3)),
    'rate_limit_per_minute': int(os.getenv('RATE_LIMIT', 300)),  # Max commands per minute per connection (increased for responsiveness, 100 is good)
    'enable_encryption': os.getenv('ENABLE_ENCRYPTION', 'true').lower() == 'true',
    'secret_key': os.getenv('SECRET_KEY', 'virtual-keyboard-secret-key-change-in-production'),
}

# Performance configuration
PERFORMANCE_CONFIG: Dict[str, Any] = {
    'enable_compression': os.getenv('ENABLE_COMPRESSION', 'true').lower() == 'true',
    'max_message_size': int(os.getenv('MAX_MESSAGE_SIZE', 1024)),  # Max message size in bytes
    'enable_metrics': os.getenv('ENABLE_METRICS', 'true').lower() == 'true',
    'metrics_interval': int(os.getenv('METRICS_INTERVAL', 60)),  # Metrics collection interval
}

# Logging configuration
LOG_CONFIG: Dict[str, Any] = {
    'log_level': os.getenv('LOG_LEVEL', 'INFO'),  # Use DEBUG for development, INFO for production
    'log_format': '%(asctime)s - %(levelname)s - %(message)s',
    'log_dir': 'logs',
} 