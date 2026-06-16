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

Owns the host's pairing secret — the root of trust, generated fresh each run and
shown only in the QR code, never sent over the network — and the per-session key
derivation and AES-256-GCM encryption built on it.

A client that scanned the QR holds the same pairing secret and derives the same
per-session key from the salt the host sends in the handshake. Possession of that
key is the client's authorization: a message that authenticates under it came from a
paired client and was not tampered with. A message that does not authenticate is a
hard error — the caller closes the connection; there is no plaintext fallback.
"""

import base64
import hashlib
import hmac
import secrets
import time
from typing import Dict, List

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .logger import get_logger

logger = get_logger(__name__)

PAIRING_SECRET_BYTES = 32   # 256-bit root secret
SESSION_SALT_BYTES = 16
NONCE_BYTES = 12            # AES-GCM nonce
TAG_BYTES = 16             # AES-GCM tag


class SecurityManager:
    """Manages the pairing secret, per-session key derivation, and message encryption."""

    def __init__(self, enable_encryption: bool = True) -> None:
        """
        Args:
            enable_encryption: When False, the host runs without encryption (local
                testing only); no key is derived and messages are handled in plaintext.
        """
        self.enable_encryption = enable_encryption
        # Random per host run. Delivered out-of-band via the QR; never transmitted.
        self._pairing_secret = secrets.token_bytes(PAIRING_SECRET_BYTES)
        if enable_encryption:
            logger.info("Pairing secret generated for this session")

    def pairing_secret_b64(self) -> str:
        """The pairing secret encoded for the QR (URL-safe base64, no padding)."""
        return base64.urlsafe_b64encode(self._pairing_secret).decode("utf-8").rstrip("=")

    def regenerate_pairing_secret(self) -> None:
        """
        Replace the pairing secret with a fresh random one (re-pairing).

        The reassignment is atomic, so a connection deriving a key concurrently reads
        either the old or the new secret cleanly. New scans must use the new QR; existing
        connections keep the key they already derived until they reconnect.
        """
        self._pairing_secret = secrets.token_bytes(PAIRING_SECRET_BYTES)
        logger.info("Pairing secret regenerated")

    def new_session_salt(self) -> bytes:
        """A fresh random salt for one connection."""
        return secrets.token_bytes(SESSION_SALT_BYTES)

    def derive_session_key(self, salt: bytes) -> bytes:
        """
        Derive this connection's AES-256 key: HMAC-SHA256(pairing_secret, salt).

        Distinct per connection (the salt is fresh each time) and identical to what a
        client holding the same pairing secret derives from the same salt.
        """
        return hmac.new(self._pairing_secret, salt, hashlib.sha256).digest()

    def encrypt(self, message: str, key: bytes) -> str:
        """Encrypt with AES-256-GCM under the session key; return URL-safe base64 (no padding)."""
        nonce = secrets.token_bytes(NONCE_BYTES)
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(message.encode("utf-8"))
        encryptor.finalize()
        data = nonce + ciphertext + encryptor.tag
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    def decrypt(self, token: str, key: bytes) -> str:
        """
        Decrypt and authenticate a message under the session key.

        Raises:
            Exception: on any failure (bad base64, wrong key, tampered ciphertext). The
                caller must treat this as a hard error and close the connection — there
                is deliberately no plaintext fallback.
        """
        # Drop all whitespace: some base64 encoders (Android's) wrap lines every 76 chars,
        # and the client omits padding — restore both before decoding.
        cleaned = "".join(token.split())
        padding = (-len(cleaned)) % 4
        raw = base64.urlsafe_b64decode(cleaned + ("=" * padding))
        if len(raw) < NONCE_BYTES + TAG_BYTES:
            raise ValueError("ciphertext too short")
        nonce = raw[:NONCE_BYTES]
        tag = raw[-TAG_BYTES:]
        ciphertext = raw[NONCE_BYTES:-TAG_BYTES]
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext.decode("utf-8")

    def hash_client_identifier(self, identifier: str) -> str:
        """A short, stable key for rate-limiting (anonymizes the raw IP in the map)."""
        return hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:16]


class RateLimiter:
    """Sliding-window rate limiter, bounded: clients with no recent requests are evicted."""

    def __init__(self, max_requests: int = 100, window_minutes: int = 1) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        recent = [t for t in self.requests.get(client_id, []) if now - t < self.window_seconds]
        if len(recent) >= self.max_requests:
            self.requests[client_id] = recent
            logger.warning("Rate limit exceeded for a client")
            return False
        recent.append(now)
        self.requests[client_id] = recent
        self._evict_idle(now)
        return True

    def _evict_idle(self, now: float) -> None:
        """Drop clients whose requests have all aged out, so the map can't grow unbounded."""
        idle = [
            cid for cid, times in self.requests.items()
            if not times or now - times[-1] >= self.window_seconds
        ]
        for cid in idle:
            del self.requests[cid]

    def get_remaining_requests(self, client_id: str) -> int:
        now = time.time()
        recent = [t for t in self.requests.get(client_id, []) if now - t < self.window_seconds]
        return max(0, self.max_requests - len(recent))
