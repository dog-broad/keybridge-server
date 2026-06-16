# Copyright 2025 Rushyendra Guntupalli (dog-broad) and Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Configuration settings for the KeyBridge server.
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

# Security configuration. The encryption key is not configured here: the host generates
# a random pairing secret each run and delivers it via the QR (see utils/security.py).
SECURITY_CONFIG: Dict[str, Any] = {
    'rate_limit_per_minute': int(os.getenv('RATE_LIMIT', 300)),  # Max commands per minute per connection
    'enable_encryption': os.getenv('ENABLE_ENCRYPTION', 'true').lower() == 'true',
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