# Virtual Keyboard Server

A WebSocket server that receives keyboard input from mobile devices and simulates typing on the host computer.

## Features

- WebSocket server for real-time communication
- Keyboard simulation using pynput
- Comprehensive logging system
- JSON-based message protocol
- Support for text typing and special key combinations
- QR code generation for easy connection setup
- Connection management with session tracking

## Requirements

- Python 3.8 or higher
- Windows 10/11

## Setup

1. Create and activate virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python src/main.py
```

The server will start and display a QR code that can be scanned by the mobile app to establish a connection.

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

### Special Keys
- `home`, `end`, `page_up`, `page_down`
- `insert`, `delete`
- `caps_lock`, `num_lock`, `scroll_lock`
- `print_screen`, `prtsc`, `prtscr`
- `pause`, `break`
- `menu`, `apps`

### Media Keys
- `media_play_pause`, `media_volume_up`, `media_volume_down`
- `media_volume_mute`, `media_next`, `media_previous`

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
│       └── qr_utils.py            # QR code generation utilities
├── logs/                          # Log files directory
├── requirements.txt               # Python dependencies
└── README.md                     # This file
```

## Configuration

The server can be configured by modifying `src/config.py`:

- `SERVER_CONFIG`: WebSocket server settings
- `LOG_CONFIG`: Logging configuration

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

### Versioning

This project follows [Semantic Versioning](https://semver.org/).

## License

MIT License
