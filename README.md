# Virtual Keyboard Server

A secure WebSocket server that receives keyboard input from mobile devices and simulates typing on the host computer. Features end-to-end encryption and token-based authentication.

## Features

- **Secure WebSocket Server** for real-time communication
- **AES-256-GCM Encryption** for all message traffic
- **Token-based Authentication** with QR code setup
- **Rate Limiting** to prevent abuse
- **Keyboard Simulation** using pynput
- **Comprehensive Logging** system
- **JSON-based Protocol** with acknowledgment support
- **Connection Management** with session tracking and keep-alive
- **QR Code Generation** for easy mobile pairing

## Requirements

- Python 3.8 or higher
- Windows 10/11 (or Linux/macOS with pynput support)

## Setup

1. Create and activate virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\activate

# Activate virtual environment (Linux/macOS)
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python src/main.py
```

The server will start and display a QR code containing encrypted connection data. Scan this with the mobile app to establish a secure connection.

## Security Features

### Encryption
- **AES-256-GCM** symmetric encryption for all messages after authentication
- **PBKDF2** key derivation with SHA256 and 100,000 iterations
- Unique nonce for each encrypted message

### Authentication
- **Token-based** authentication with expiration
- Maximum authentication attempts to prevent brute force
- Session ID tracking for connection management

### Rate Limiting
- Configurable request limits per minute per connection
- Automatic rejection of excessive requests

### Configuration
Security settings can be modified in `src/config.py`:
```python
SECURITY_CONFIG = {
    'enable_authentication': True,
    'token_expiry_minutes': 60,
    'max_auth_attempts': 3,
    'rate_limit_per_minute': 100,
    'enable_encryption': True,
    'secret_key': 'your-secret-key-here',  # Change in production!
}
```

## Message Protocol

Messages are sent in JSON format with the following command types:

### Type Text
```json
{
    "command": "type",
    "text": "Hello, World!"
}
```

### Press Single Key
```json
{
    "command": "key_press",
    "key": "backspace"
}
```

### Release Single Key
```json
{
    "command": "key_release",
    "key": "shift"
}
```

### Key Combination
```json
{
    "command": "key_combo",
    "keys": ["ctrl", "c"]
}
```

### Hotkey
```json
{
    "command": "hotkey",
    "keys": ["ctrl", "alt", "delete"]
}
```

### Keep-Alive Ping
```json
{
    "command": "ping",
    "timestamp": 1701234567890
}
```

## Supported Keys

The server supports the following special keys:

### Navigation Keys
- `backspace`, `tab`, `enter`, `space`
- `esc`, `escape`

### Modifier Keys
- `shift`, `ctrl`, `alt`
- `cmd`, `command`, `windows`, `win`

### Arrow Keys
- `up`, `down`, `left`, `right`

### Function Keys
- `f1` through `f12`

### Extended Navigation
- `home`, `end`, `page_up`, `page_down`
- `insert`, `delete`

### System Keys
- `caps_lock`, `num_lock`, `scroll_lock`
- `print_screen`, `prtsc`, `prtscr`
- `pause`, `break`
- `menu`, `apps`

### Media Keys
- `media_play_pause`, `media_next`, `media_previous`
- `media_volume_up`, `media_volume_down`, `media_volume_mute`

## Response Format

All commands return a JSON response:

### Success Response
```json
{
    "status": "success",
    "message": "Successfully typed text: Hello, World!"
}
```

### Error Response
```json
{
    "status": "error",
    "message": "Error description"
}
```

### Response with Acknowledgment
```json
{
    "status": "success",
    "message": "Successfully pressed key: ctrl",
    "message_id": "uuid-here",
    "requires_ack": true
}
```

## Project Structure

```
virtual-keyboard-server/
├── src/
│   ├── main.py                    # Main server script
│   ├── config.py                  # Configuration settings
│   └── utils/
│       ├── __init__.py
│       ├── commands.py            # Command definitions and validation
│       ├── connection_manager.py  # WebSocket connection management
│       ├── keyboard_controller.py # Keyboard simulation controller
│       ├── logger.py              # Logging configuration
│       ├── message_handler.py     # Message parsing and routing
│       ├── qr_utils.py            # QR code generation utilities
│       └── security.py            # Encryption and authentication
├── logs/                          # Log files directory
├── connection_qr.png              # Generated QR code image
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Configuration

### Server Settings (config.py)
```python
SERVER_CONFIG = {
    'host': '0.0.0.0',           # Listen on all interfaces
    'port': 8765,                 # WebSocket port
    'ping_interval': 20,          # Ping every 20 seconds
    'ping_timeout': 20,           # Wait 20 seconds for pong
    'idle_timeout': 600,          # Close idle connections after 10 min
    'max_connections': 10,        # Maximum concurrent connections
}
```

### Performance Settings
```python
PERFORMANCE_CONFIG = {
    'enable_compression': True,
    'max_message_size': 1024,     # Max message size in bytes
    'enable_metrics': True,
}
```

## Troubleshooting

### Server Won't Start
- Check if port 8765 is already in use
- Ensure Python 3.8+ is installed
- Verify all dependencies are installed

### Keys Not Working
- Run the server with administrator privileges
- Check if another app is capturing keyboard input
- Verify the key name matches supported keys list

### Connection Issues
- Ensure firewall allows port 8765
- Check both devices are on the same network
- Regenerate QR code if token has expired

### Encryption Errors
- Verify same encryption key on server and client
- Check system time synchronization
- Enable debug logging to see detailed errors

## Development

### Git Workflow

1. Create a new branch for features:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and commit:
```bash
git add .
git commit -m "Description of changes"
```

3. Push changes:
```bash
git push origin feature/your-feature-name
```

### Running Tests
```bash
python -m pytest tests/
```

### Versioning

This project follows [Semantic Versioning](https://semver.org/).

## License

MIT License
