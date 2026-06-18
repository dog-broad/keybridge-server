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
KeyBridge Server — headless entry point.

Runs the WebSocket host and prints the pairing QR in the terminal. For the
double-click desktop experience, run launcher.py instead.
"""

import sys

from server import KeyBridgeServer
from utils.logger import setup_logger

logger = setup_logger()


def main() -> None:
    server = KeyBridgeServer()

    print("\nKeyBridge — scan this QR code with the app to pair:\n")
    print(server.ascii_qr())
    print(f"Or connect the app manually to: {server.pairing_url}")
    if server.encryption_enabled:
        print("Encrypted: the pairing key travels only in the QR, never over the network.")
    else:
        print("Local plaintext mode (no encryption).")
    print("\nServer running. Press Ctrl+C to stop.\n")

    server.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        logger.info("Stopped.")
