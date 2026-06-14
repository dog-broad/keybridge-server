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
Security Module

This module handles authentication, token generation, and encryption for the KeyBridge server.
"""

import hashlib
import hmac
import json
import secrets
import time
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import struct
from .logger import get_logger

logger = get_logger(__name__)

class SecurityManager:
    """Handles security operations including authentication and encryption."""
    
    def __init__(self, secret_key: str, enable_encryption: bool = True):
        """
        Initialize the security manager.
        
        Args:
            secret_key: Secret key for token signing and encryption
            enable_encryption: Whether to enable message encryption
        """
        self.secret_key = secret_key.encode('utf-8')
        self.enable_encryption = enable_encryption
        self._encryption_key = None
        
        if enable_encryption:
            # Derive encryption key from secret key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256-bit key for AES-256
                salt=b'keybridge_salt',
                iterations=100000,
            )
            self._encryption_key = kdf.derive(self.secret_key)
            logger.info("AES-GCM encryption initialized")
            logger.info(f"PBKDF2 key derivation:")
            logger.info(f"Secret key: {self.secret_key.decode()}")
            logger.info(f"Salt: keybridge_salt")
            logger.info(f"Iterations: 100000")
            logger.info(f"Key length: 32 bytes")
            logger.info(f"Derived key (hex): {self._encryption_key.hex()}")
    
    def generate_connection_token(self, expiry_minutes: int = 60) -> Tuple[str, float]:
        """
        Generate a secure connection token for QR codes.
        
        Args:
            expiry_minutes: Token expiry time in minutes
            
        Returns:
            Tuple of (token, expiry_timestamp)
        """
        # Generate random token data
        token_data = {
            'id': secrets.token_hex(16),
            'created': time.time(),
            'expires': time.time() + (expiry_minutes * 60),
            'nonce': secrets.token_hex(8)
        }
        
        # Create token payload
        payload = json.dumps(token_data, separators=(',', ':')).encode('utf-8')
        
        # Sign the token with HMAC
        signature = hmac.new(
            self.secret_key,
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Combine payload and signature
        token = base64.urlsafe_b64encode(payload).decode('utf-8') + '.' + signature
        
        logger.info(f"Generated connection token with ID: {token_data['id']}")
        return token, token_data['expires']
    
    def validate_connection_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a connection token.
        
        Args:
            token: Token to validate
            
        Returns:
            Token data if valid, None otherwise
        """
        try:
            # Split token and signature
            if '.' not in token:
                logger.warning("Invalid token format - missing signature")
                return None
                
            encoded_payload, signature = token.rsplit('.', 1)
            
            # Decode payload
            payload = base64.urlsafe_b64decode(encoded_payload.encode('utf-8'))
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key,
                payload,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Token signature verification failed")
                return None
            
            # Parse token data
            token_data = json.loads(payload.decode('utf-8'))
            
            # Check expiry
            if time.time() > token_data['expires']:
                logger.warning(f"Token expired: {token_data['id']}")
                return None
            
            logger.info(f"Token validated successfully: {token_data['id']}")
            return token_data
            
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return None
    
    def encrypt_message(self, message: str) -> str:
        """
        Encrypt a message using AES-GCM if encryption is enabled.
        
        Args:
            message: Message to encrypt
            
        Returns:
            Encrypted message or original message if encryption disabled
        """
        if not self.enable_encryption or not self._encryption_key:
            return message
        
        try:
            # Generate random nonce (12 bytes for GCM)
            nonce = secrets.token_bytes(12)
            
            # Encrypt using AES-GCM
            cipher = Cipher(
                algorithms.AES(self._encryption_key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Encrypt the message
            ciphertext = encryptor.update(message.encode('utf-8'))
            encryptor.finalize()  # Finalize to make tag available
            
            # Get the authentication tag
            tag = encryptor.tag
            
            # Combine nonce + ciphertext + tag (matching Android format)
            encrypted_data = nonce + ciphertext + tag
            
            # Encode as base64
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Message encryption failed: {str(e)}")
            return message
    
    def decrypt_message(self, encrypted_message: str) -> Optional[str]:
        """
        Decrypt a message using AES-GCM if encryption is enabled.
        
        Args:
            encrypted_message: Message to decrypt
            
        Returns:
            Decrypted message or None if decryption failed
        """
        if not self.enable_encryption or not self._encryption_key:
            return encrypted_message
        
        try:
            # Android encodes without base64 padding; restore it before decoding.
            missing_padding = len(encrypted_message) % 4
            if missing_padding:
                encrypted_message = encrypted_message + '=' * (4 - missing_padding)

            encrypted_data = base64.urlsafe_b64decode(encrypted_message.encode('utf-8'))

            # Layout matches the client: nonce (12 bytes) + ciphertext + tag (16 bytes).
            if len(encrypted_data) < 28:  # 12 (nonce) + 0 (ciphertext) + 16 (tag)
                raise ValueError("Encrypted data too short")

            nonce = encrypted_data[:12]
            tag = encrypted_data[-16:]
            ciphertext = encrypted_data[12:-16]

            # Decrypt using AES-GCM with separate tag
            cipher = Cipher(
                algorithms.AES(self._encryption_key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            decrypted = decryptor.update(ciphertext) + decryptor.finalize()
            return decrypted.decode('utf-8')
        except Exception as e:
            # Never log the payload or key material; a one-line cause is enough.
            logger.error(f"Message decryption failed: {type(e).__name__}: {e}")
            return None
    
    def hash_client_identifier(self, identifier: str) -> str:
        """
        Create a hash of client identifier for rate limiting.
        
        Args:
            identifier: Client identifier (usually IP address)
            
        Returns:
            Hashed identifier
        """
        return hashlib.sha256(f"{identifier}:{self.secret_key.decode()}".encode()).hexdigest()[:16]

class RateLimiter:
    """Simple rate limiter for connection and command throttling."""
    
    def __init__(self, max_requests: int = 100, window_minutes: int = 1):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in window
            window_minutes: Time window in minutes
        """
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if client is allowed to make a request.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        
        # Initialize client request history
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests outside the window
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[client_id]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return False
        
        # Record this request
        self.requests[client_id].append(now)
        return True
    
    def get_remaining_requests(self, client_id: str) -> int:
        """
        Get remaining requests for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Number of remaining requests
        """
        if client_id not in self.requests:
            return self.max_requests
        
        now = time.time()
        recent_requests = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < self.window_seconds
        ]
        
        return max(0, self.max_requests - len(recent_requests))
