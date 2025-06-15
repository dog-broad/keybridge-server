import qrcode
import os
from typing import Tuple
import socket
import logging
import sys
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

def generate_connection_qr(port: int, save_path: str = "connection_qr.png") -> Tuple[str, str]:
    """
    Generate a QR code containing the connection information (IP:port).
    
    Args:
        port (int): The port number to include in the QR code
        save_path (str): Path where to save the QR code image
        
    Returns:
        Tuple[str, str]: (connection_string, qr_path)
    """
    ip = get_local_ip()
    connection_string = f"{ip}:{port}"
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Add data
    qr.add_data(connection_string)
    qr.make(fit=True)
    
    # Create an image from the QR Code
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
    
    # Save the image
    qr_image.save(save_path)
    logger.info(f"QR code generated and saved to {save_path}")
    
    return connection_string, save_path

def generate_ascii_qr(port: int) -> str:
    """
    Generate an ASCII representation of the QR code for terminal display.
    
    Args:
        port (int): The port number to include in the QR code
        
    Returns:
        str: ASCII representation of the QR code
    """
    ip = get_local_ip()
    connection_string = f"{ip}:{port}"
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1,
    )
    
    # Add data
    qr.add_data(connection_string)
    qr.make(fit=True)
    
    # Generate ASCII representation
    ascii_qr = qr.get_matrix()
    ascii_str = ""
    
    for row in ascii_qr:
        for cell in row:
            ascii_str += "██" if cell else "  "
        ascii_str += "\n"
    
    return ascii_str

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
        
        # Generate new QR code
        connection_string, qr_path = generate_connection_qr(port, output_path)
        logger.info(f"Generated QR code for connection string: {connection_string}")
        logger.info(f"QR code saved to: {qr_path}")
        
        if show_ascii:
            ascii_qr = generate_ascii_qr(port)
            print("\nASCII QR Code:")
            print(ascii_qr)
            print(f"Connection string: {connection_string}")
            
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