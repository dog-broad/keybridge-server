# Virtual Keyboard Server

A WebSocket server that receives keyboard input from mobile devices and simulates typing on the host computer.

## Features

- WebSocket server for real-time communication
- Keyboard simulation using pynput
- Comprehensive logging system
- JSON-based message protocol

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

## Message Protocol

Messages are sent in JSON format:
```json
{
    "type": "key",
    "value": "a"
}
```

## Project Structure

```
virtual-keyboard-server/
├── src/
│   ├── main.py           # Main server script
│   └── utils/
│       └── logger.py     # Logging configuration
├── logs/                 # Log files directory
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

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
