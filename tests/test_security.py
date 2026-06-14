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

"""Tests for pairing-secret key derivation, AES-GCM encrypt/decrypt, and the rate limiter."""

import base64
import time

import pytest

from utils.security import RateLimiter, SecurityManager


def _b64decode(s):
    return base64.urlsafe_b64decode(s + "=" * ((-len(s)) % 4))


# --- pairing secret + key derivation -------------------------------------------

def test_pairing_secret_is_32_bytes_and_random_per_instance():
    a = SecurityManager()
    b = SecurityManager()
    assert len(_b64decode(a.pairing_secret_b64())) == 32
    assert a.pairing_secret_b64() != b.pairing_secret_b64()


def test_derive_session_key_is_deterministic_for_a_salt():
    sm = SecurityManager()
    salt = sm.new_session_salt()
    key = sm.derive_session_key(salt)
    assert len(key) == 32
    assert sm.derive_session_key(salt) == key


def test_derive_session_key_differs_by_salt():
    sm = SecurityManager()
    assert sm.derive_session_key(sm.new_session_salt()) != sm.derive_session_key(sm.new_session_salt())


def test_two_hosts_with_different_secrets_derive_different_keys():
    a, b = SecurityManager(), SecurityManager()
    salt = a.new_session_salt()
    assert a.derive_session_key(salt) != b.derive_session_key(salt)


# --- encrypt / decrypt ----------------------------------------------------------

def test_encrypt_decrypt_round_trip_unicode():
    sm = SecurityManager()
    key = sm.derive_session_key(sm.new_session_salt())
    message = 'café résumé 😀 测试 {"v":1}'
    assert sm.decrypt(sm.encrypt(message, key), key) == message


def test_decrypt_with_wrong_key_raises():
    sm = SecurityManager()
    key = sm.derive_session_key(sm.new_session_salt())
    token = sm.encrypt("secret", key)
    wrong = sm.derive_session_key(sm.new_session_salt())
    with pytest.raises(Exception):
        sm.decrypt(token, wrong)


def test_decrypt_tampered_ciphertext_raises():
    sm = SecurityManager()
    key = sm.derive_session_key(sm.new_session_salt())
    token = sm.encrypt("secret", key)
    flipped = "A" if token[10] != "A" else "B"
    tampered = token[:10] + flipped + token[11:]
    with pytest.raises(Exception):
        sm.decrypt(tampered, key)


def test_decrypt_rejects_garbage():
    sm = SecurityManager()
    key = sm.derive_session_key(sm.new_session_salt())
    with pytest.raises(Exception):
        sm.decrypt("not-valid-base64-or-ciphertext", key)


# --- rate limiter ---------------------------------------------------------------

def test_rate_limiter_allows_up_to_max_then_blocks():
    rl = RateLimiter(max_requests=3, window_minutes=1)
    assert [rl.is_allowed("c") for _ in range(3)] == [True, True, True]
    assert rl.is_allowed("c") is False


def test_rate_limiter_evicts_idle_clients():
    rl = RateLimiter(max_requests=5, window_minutes=1)
    rl.is_allowed("idle")
    # Age the idle client's only request past the window, then drive another client.
    rl.requests["idle"] = [time.time() - 999]
    rl.is_allowed("active")
    assert "idle" not in rl.requests   # evicted
    assert "active" in rl.requests
