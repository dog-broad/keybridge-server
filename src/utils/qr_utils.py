"""
QR Code Generation Utilities

This module provides utilities for generating QR codes for WebSocket connection strings
with secure authentication tokens.
"""

import json
import os
import qrcode
import socket
import logging
import sys
from typing import Tuple, Optional
from pathlib import Path

# Add the parent directory to sys.path when running as standalone script
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent))

try:
    from .logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    # Fallback logging setup for standalone usage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

def get_local_ip() -> str:
    """Get the local IP address of the machine."""
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.error(f"Failed to get local IP: {e}")
        return "127.0.0.1"  # Fallback to localhost

def generate_connection_qr(
    port: int, 
    security_manager=None,
    save_path: str = "connection_qr.png"
) -> Tuple[str, str]:
    """
    Generate a QR code containing the WebSocket connection string with authentication token.
    
    Args:
        port (int): WebSocket server port
        security_manager: Security manager for token generation (optional)
        save_path (str): Path to save the QR code image
        
    Returns:
        Tuple[str, str]: Connection data (JSON string) and QR code image path
    """
    local_ip = get_local_ip()
    
    # Create connection data
    connection_data = {
        "version": "2.0",
        "url": f"ws://{local_ip}:{port}",
        "protocol": "virtual-keyboard-v2"
    }
    
    # Add authentication token if security manager is provided
    if security_manager:
        try:
            token, expiry = security_manager.generate_connection_token()
            connection_data["auth"] = {
                "token": token,
                "expires": expiry,
                "type": "bearer"
            }
            logger.info("Generated QR code with authentication token")
        except Exception as e:
            logger.warning(f"Failed to generate auth token: {e}")
            logger.info("Generated QR code without authentication (fallback)")
    else:
        logger.info("Generated QR code without authentication (legacy mode)")
    
    # Convert to JSON string
    connection_string = json.dumps(connection_data, separators=(',', ':'))
    
    # Create QR code
    qr = qrcode.QRCode(
        version=None,  # Auto-determine version based on data
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # Medium error correction for tokens
        box_size=10,
        border=4,
    )
    
    qr.add_data(connection_string)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
    
    # Save the image
    img.save(save_path)
    
    logger.info(f"QR code generated and saved to: {save_path}")
    return connection_string, save_path

def generate_ascii_qr(
    port: int, 
    security_manager=None
) -> str:
    """
    Generate an ASCII QR code for terminal display.
    
    Args:
        port (int): WebSocket server port
        security_manager: Security manager for token generation (optional)
        
    Returns:
        str: ASCII QR code
    """
    local_ip = get_local_ip()
    
    # Create connection data
    connection_data = {
        "version": "2.0",
        "url": f"ws://{local_ip}:{port}",
        "protocol": "virtual-keyboard-v2"
    }
    
    # Add authentication token if security manager is provided
    if security_manager:
        try:
            token, expiry = security_manager.generate_connection_token()
            connection_data["auth"] = {
                "token": token,
                "expires": expiry,
                "type": "bearer"
            }
        except Exception as e:
            logger.warning(f"Failed to generate auth token: {e}")
    
    # Convert to JSON string
    connection_string = json.dumps(connection_data, separators=(',', ':'))
    
    # Create QR code
    qr = qrcode.QRCode(
        version=None,  # Auto-determine version
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=1,
    )
    
    qr.add_data(connection_string)
    qr.make(fit=True)
    
    # Generate ASCII representation
    ascii_qr = qr.get_matrix()
    
    # Convert to ASCII characters
    ascii_string = ""
    for row in ascii_qr:
        line = ""
        for cell in row:
            line += "██" if cell else "  "  # Use double-width characters for better visibility
        ascii_string += line + "\n"
    
    return ascii_string

def parse_connection_qr(qr_data: str) -> dict:
    """
    Parse connection data from QR code.
    
    Args:
        qr_data: QR code data string
        
    Returns:
        dict: Parsed connection data
        
    Raises:
        ValueError: If QR data is invalid
    """
    try:
        # Try to parse as JSON (new format)
        data = json.loads(qr_data)
        if isinstance(data, dict) and "url" in data:
            return data
    except json.JSONDecodeError:
        pass
    
    # Try legacy format (plain IP:port or WebSocket URL)
    if ':' in qr_data:
        # Handle legacy IP:port format
        if qr_data.startswith(('ws://', 'wss://')):
            url = qr_data
        else:
            # Convert IP:port to WebSocket URL
            url = f"ws://{qr_data}"
        
        return {
            "version": "1.0",
            "url": url,
            "protocol": "virtual-keyboard-v1"
        }
    
    raise ValueError("Invalid QR code data format")

def regenerate_qr(port: int, output_path: str = "connection_qr.png", show_ascii: bool = False) -> None:
    """
    Regenerate QR code with the given port and options.
    
    Args:
        port (int): Port number for the connection
        output_path (str): Path to save the QR code image
        show_ascii (bool): Whether to display ASCII version in terminal
    """
    try:
        # Get current IP
        current_ip = get_local_ip()
        logger.info(f"Current IP address: {current_ip}")
        
        # Generate new QR code (without security manager for standalone usage)
        connection_string, qr_path = generate_connection_qr(port, None, output_path)
        logger.info(f"Generated QR code for connection string: {connection_string}")
        logger.info(f"QR code saved to: {qr_path}")
        
        if show_ascii:
            ascii_qr = generate_ascii_qr(port, None)
            print("\nASCII QR Code:")
            print(ascii_qr)
            print(f"Connection data: {connection_string}")
            
    except Exception as e:
        logger.error(f"Failed to regenerate QR code: {e}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Regenerate QR code for Virtual Keyboard Server')
    parser.add_argument('--port', type=int, required=True, help='Port number for the server')
    parser.add_argument('--output', type=str, default='connection_qr.png',
                      help='Output path for the QR code image (default: connection_qr.png)')
    parser.add_argument('--ascii', action='store_true',
                      help='Display ASCII version of the QR code in terminal')
    
    args = parser.parse_args()
    
    try:
        regenerate_qr(args.port, args.output, args.ascii)
    except Exception as e:
        sys.exit(1)