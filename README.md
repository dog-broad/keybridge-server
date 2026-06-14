<div align="center">

# KeyBridge Server

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/dog-broad/keybridge-server)

A secure WebSocket server that receives keyboard input from mobile devices and simulates typing on the host computer. Features end-to-end encryption and token-based authentication.

---

### 📱 **This server requires the KeyBridge Android App**

**[➡️ Get KeyBridge Android App](https://github.com/dog-broad/KeyBridge)**

Both components work together to provide secure remote keyboard control.

---

</div>

## Features

- **Secure WebSocket Server** for real-time communication
- **AES-256-GCM Encryption** for all message traffic
- **Token-based Authentication** with QR code setup
- **Rate Limiting** to prevent abuse
- **Keyboard Simulation** using pynput
- **Comprehensive Logging** system
- **Versioned message protocol** with per-chunk delivery acknowledgement
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
Security settings can be modified via environment variables in `src/.env`:
```bash
# Security Configuration
SECRET_KEY=your-strong-random-secret-key-here  # REQUIRED: Change from default!
ENABLE_AUTH=true
TOKEN_EXPIRY=60
MAX_AUTH_ATTEMPTS=3
RATE_LIMIT=300
ENABLE_ENCRYPTION=true
```

**⚠️ SECURITY WARNING**: The default secret key is for development only. **You must set a strong `SECRET_KEY` in production!** See [SECURITY.md](SECURITY.md) for details.

## Message Protocol

Input travels in a small versioned envelope, and the server acknowledges every chunk it
applies, so the client knows what landed. Long text is split into ordered chunks the
client can track as progress. The full contract — envelope fields, input types, the
acknowledgement shape, chunking, and idempotent retry — is specified in
**[PROTOCOL.md](PROTOCOL.md)**.

A `type` message, for example, looks like:

```json
{ "v": 1, "id": "…", "seq": 0, "total": 1, "type": "type",
  "payload": { "text": "Hello, World!" } }
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

## Acknowledgements

The server confirms each applied chunk with an `ack` that echoes the message `id` and
chunk `seq`:

```json
{ "v": 1, "type": "ack", "id": "…", "seq": 0, "status": "ok" }
```

A failure to apply a chunk returns `"status": "error"` with a reason. See
[PROTOCOL.md](PROTOCOL.md) for the full acknowledgement and retry semantics.

## Project Structure

```
keybridge-server/
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
├── LICENSE                        # Apache License 2.0
├── NOTICE                         # Third-party notices
├── PROTOCOL.md                    # Wire protocol contract
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

Apache License 2.0

See the [LICENSE](LICENSE) file for details.
