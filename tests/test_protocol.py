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

"""Tests for the versioned envelope: parsing, payload validation, de-dupe, routing."""

import asyncio

import pytest

from utils.commands import CommandValidator
from utils.envelope import (
    EnvelopeError,
    EnvelopeType,
    SeenChunks,
    build_ack,
    parse_envelope,
)
from utils.message_handler import MessageHandler


def env(**overrides):
    """A valid single-chunk 'type' envelope, with field overrides for negative cases."""
    base = {"v": 1, "id": "m1", "seq": 0, "total": 1, "type": "type", "payload": {"text": "hi"}}
    base.update(overrides)
    return base


def run(coro):
    return asyncio.run(coro)


class FakeKeyboard:
    """Records calls instead of driving the real keyboard."""

    def __init__(self):
        self.calls = []

    def type_text(self, text, delay_ms=0):
        self.calls.append(("type", text, delay_ms))

    def press_key(self, key):
        self.calls.append(("press", key))

    def release_key(self, key):
        self.calls.append(("release", key))


def make_handler():
    handler = MessageHandler()
    handler.keyboard = FakeKeyboard()
    return handler


# --- parse_envelope -------------------------------------------------------------

def test_parse_valid_envelope():
    e = parse_envelope(env())
    assert (e.v, e.id, e.seq, e.total, e.type) == (1, "m1", 0, 1, EnvelopeType.TYPE)
    assert e.payload == {"text": "hi"}


def test_parse_rejects_unknown_version_and_carries_chunk_ids():
    with pytest.raises(EnvelopeError) as exc:
        parse_envelope(env(v=2))
    # id/seq are carried so the caller can address an error ack at the chunk.
    assert exc.value.msg_id == "m1" and exc.value.seq == 0


def test_parse_rejects_missing_id():
    with pytest.raises(EnvelopeError):
        parse_envelope(env(id=""))


def test_parse_rejects_boolean_seq():
    # JSON booleans must not be accepted where an integer seq is required.
    with pytest.raises(EnvelopeError):
        parse_envelope(env(seq=True))


def test_parse_rejects_negative_seq():
    with pytest.raises(EnvelopeError):
        parse_envelope(env(seq=-1, total=2))


def test_parse_rejects_total_below_one():
    with pytest.raises(EnvelopeError):
        parse_envelope(env(total=0))


def test_parse_rejects_seq_not_less_than_total():
    with pytest.raises(EnvelopeError):
        parse_envelope(env(seq=2, total=2))


def test_parse_rejects_unknown_type():
    with pytest.raises(EnvelopeError):
        parse_envelope(env(type="mouse_click"))


def test_parse_rejects_non_object_payload():
    with pytest.raises(EnvelopeError):
        parse_envelope(env(payload="oops"))


def test_parse_allows_missing_payload():
    e = parse_envelope({"v": 1, "id": "m1", "seq": 0, "total": 1, "type": "key_press"})
    assert e.payload == {}


# --- build_ack ------------------------------------------------------------------

def test_build_ack_ok():
    assert build_ack("m1", 3) == {"v": 1, "type": "ack", "id": "m1", "seq": 3, "status": "ok"}


def test_build_ack_error_includes_reason():
    ack = build_ack("m1", 0, "error", "bad key")
    assert ack["status"] == "error" and ack["error"] == "bad key"


# --- SeenChunks -----------------------------------------------------------------

def test_seen_chunks_dedupe_is_idempotent():
    seen = SeenChunks()
    assert not seen.has("m1", 0)
    seen.add("m1", 0)
    seen.add("m1", 0)
    assert seen.has("m1", 0)


def test_seen_chunks_evicts_oldest_past_bound():
    seen = SeenChunks(max_entries=2)
    seen.add("a", 0)
    seen.add("b", 0)
    seen.add("c", 0)
    assert not seen.has("a", 0)
    assert seen.has("b", 0) and seen.has("c", 0)


# --- CommandValidator.validate_payload ------------------------------------------

def test_validate_type_payload_ok():
    CommandValidator.validate_payload(EnvelopeType.TYPE, {"text": "hi", "delay_ms": 10})


def test_validate_type_payload_requires_text():
    with pytest.raises(ValueError):
        CommandValidator.validate_payload(EnvelopeType.TYPE, {})


def test_validate_type_payload_rejects_empty_string():
    with pytest.raises(ValueError):
        CommandValidator.validate_payload(EnvelopeType.TYPE, {"text": ""})


def test_validate_type_payload_allows_whitespace_chunk():
    # A chunk that is all whitespace is valid input mid-paste; it must not be rejected.
    CommandValidator.validate_payload(EnvelopeType.TYPE, {"text": "   \n  "})


def test_validate_type_payload_rejects_negative_delay():
    with pytest.raises(ValueError):
        CommandValidator.validate_payload(EnvelopeType.TYPE, {"text": "x", "delay_ms": -1})


def test_validate_key_payload_accepts_name_and_single_char():
    CommandValidator.validate_payload(EnvelopeType.KEY_PRESS, {"key": "ctrl"})
    CommandValidator.validate_payload(EnvelopeType.KEY_RELEASE, {"key": "a"})


def test_validate_key_payload_rejects_unknown_key():
    with pytest.raises(ValueError):
        CommandValidator.validate_payload(EnvelopeType.KEY_PRESS, {"key": "notakey"})


def test_validate_combo_payload_ok():
    CommandValidator.validate_payload(EnvelopeType.KEY_COMBO, {"keys": ["ctrl", "c"]})


def test_validate_combo_payload_rejects_empty():
    with pytest.raises(ValueError):
        CommandValidator.validate_payload(EnvelopeType.KEY_COMBO, {"keys": []})


def test_validate_rejects_ack_as_input():
    with pytest.raises(ValueError):
        CommandValidator.validate_payload(EnvelopeType.ACK, {})


# --- MessageHandler.handle_envelope ---------------------------------------------

def test_handle_type_applies_and_acks_and_records():
    handler = make_handler()
    seen = SeenChunks()
    ack = run(handler.handle_envelope(parse_envelope(env(payload={"text": "hello", "delay_ms": 5})), seen))
    assert ack == {"v": 1, "type": "ack", "id": "m1", "seq": 0, "status": "ok"}
    assert handler.keyboard.calls == [("type", "hello", 5)]
    assert seen.has("m1", 0)


def test_handle_duplicate_chunk_reacks_without_reapplying():
    handler = make_handler()
    seen = SeenChunks()
    e = parse_envelope(env(payload={"text": "x"}))
    run(handler.handle_envelope(e, seen))
    ack = run(handler.handle_envelope(e, seen))
    assert ack["status"] == "ok"
    assert handler.keyboard.calls == [("type", "x", 0)]  # applied exactly once


def test_handle_invalid_payload_error_ack_not_recorded():
    handler = make_handler()
    seen = SeenChunks()
    ack = run(handler.handle_envelope(parse_envelope(env(payload={})), seen))  # missing 'text'
    assert ack["status"] == "error" and "error" in ack
    assert handler.keyboard.calls == []
    assert not seen.has("m1", 0)


def test_handle_combo_presses_in_order_releases_reversed():
    handler = make_handler()
    seen = SeenChunks()
    e = parse_envelope(env(type="key_combo", payload={"keys": ["ctrl", "c"]}))
    run(handler.handle_envelope(e, seen))
    assert handler.keyboard.calls == [
        ("press", "ctrl"), ("press", "c"), ("release", "c"), ("release", "ctrl"),
    ]


def test_handle_apply_failure_errors_and_does_not_record():
    handler = make_handler()
    seen = SeenChunks()

    def boom(text, delay_ms=0):
        raise RuntimeError("keyboard unavailable")

    handler.keyboard.type_text = boom
    ack = run(handler.handle_envelope(parse_envelope(env(payload={"text": "x"})), seen))
    assert ack["status"] == "error"
    assert not seen.has("m1", 0)
