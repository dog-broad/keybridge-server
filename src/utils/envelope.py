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
Protocol Envelope Module

Defines the versioned message envelope that carries input and delivery
acknowledgements, parses and structurally validates incoming envelopes, builds
acks, and tracks applied chunks for idempotent retry.

The envelope is the contract shared with the client:

    {
      "v": 1,          # protocol version
      "id": "uuid",    # unique per logical message (idempotency key)
      "seq": 0,        # 0-based chunk index within the message
      "total": 1,      # total chunks in the message
      "type": "type",  # type | key_press | key_release | key_combo | ack
      "payload": { }   # type-specific body (absent on ack)
    }
"""

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Deque, Dict, Optional, Set, Tuple

# The envelope version this server speaks. A message with any other version is
# rejected rather than applied, so a client built against a different protocol
# can never have its input silently misinterpreted.
PROTOCOL_VERSION = 1


class EnvelopeType(str, Enum):
    """The input families carried by the envelope, plus the acknowledgement."""

    TYPE = "type"
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    KEY_COMBO = "key_combo"
    ACK = "ack"


@dataclass(frozen=True)
class Envelope:
    """A parsed, structurally valid envelope. Payload contents are validated separately."""

    v: int
    id: str
    seq: int
    total: int
    type: EnvelopeType
    payload: Dict[str, Any]


class EnvelopeError(ValueError):
    """
    Raised when an incoming envelope is malformed or unsupported.

    Carries whatever ``id``/``seq`` could be read before validation failed, so the
    caller can address an error ack at the specific chunk when those are available.
    """

    def __init__(self, message: str, msg_id: Optional[str] = None, seq: Optional[int] = None) -> None:
        super().__init__(message)
        self.msg_id = msg_id
        self.seq = seq


def _is_int(value: Any) -> bool:
    # bool is a subclass of int; a JSON boolean is not a valid seq/total/version.
    return isinstance(value, int) and not isinstance(value, bool)


def parse_envelope(data: Any) -> Envelope:
    """
    Validate the envelope structure and return an :class:`Envelope`.

    Raises:
        EnvelopeError: if any required field is missing, mistyped, or out of range,
            or if the protocol version or type is unsupported.
    """
    if not isinstance(data, dict):
        raise EnvelopeError("Envelope must be a JSON object")

    # Read id/seq up front so an error ack can target the chunk even when later
    # fields are invalid.
    raw_id = data.get("id")
    msg_id = raw_id if isinstance(raw_id, str) and raw_id else None
    raw_seq = data.get("seq")
    seq_for_error = raw_seq if _is_int(raw_seq) else None

    version = data.get("v")
    if version != PROTOCOL_VERSION:
        raise EnvelopeError(f"Unsupported protocol version: {version!r}", msg_id, seq_for_error)

    if msg_id is None:
        raise EnvelopeError("Envelope 'id' must be a non-empty string", None, seq_for_error)

    if not _is_int(raw_seq) or raw_seq < 0:
        raise EnvelopeError("Envelope 'seq' must be a non-negative integer", msg_id, None)
    seq = raw_seq

    raw_total = data.get("total")
    if not _is_int(raw_total) or raw_total < 1:
        raise EnvelopeError("Envelope 'total' must be an integer >= 1", msg_id, seq)
    total = raw_total

    if seq >= total:
        raise EnvelopeError("Envelope 'seq' must be less than 'total'", msg_id, seq)

    raw_type = data.get("type")
    try:
        env_type = EnvelopeType(raw_type)
    except ValueError:
        raise EnvelopeError(f"Unsupported envelope type: {raw_type!r}", msg_id, seq)

    payload = data.get("payload", {})
    if not isinstance(payload, dict):
        raise EnvelopeError("Envelope 'payload' must be a JSON object", msg_id, seq)

    return Envelope(v=version, id=msg_id, seq=seq, total=total, type=env_type, payload=payload)


def build_ack(msg_id: str, seq: int, status: str = "ok", error: Optional[str] = None) -> Dict[str, Any]:
    """Build an acknowledgement for one applied (or rejected) chunk."""
    ack: Dict[str, Any] = {
        "v": PROTOCOL_VERSION,
        "type": EnvelopeType.ACK.value,
        "id": msg_id,
        "seq": seq,
        "status": status,
    }
    if error is not None:
        ack["error"] = error
    return ack


class SeenChunks:
    """
    Bounded record of the ``(id, seq)`` chunks already applied on one connection.

    Idempotent retry depends on this: a chunk whose ``(id, seq)`` is already present
    is re-acked but not re-applied, so a client can safely resend a chunk whose ack
    was lost without the input being applied twice. The record is bounded so a
    high-churn connection cannot grow it without limit, and it lives for the lifetime
    of a single connection.
    """

    def __init__(self, max_entries: int = 256) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self._max_entries = max_entries
        self._order: Deque[Tuple[str, int]] = deque()
        self._seen: Set[Tuple[str, int]] = set()

    def has(self, msg_id: str, seq: int) -> bool:
        """Return True if this chunk was already applied."""
        return (msg_id, seq) in self._seen

    def add(self, msg_id: str, seq: int) -> None:
        """Record a chunk as applied, evicting the oldest entry past the bound."""
        key = (msg_id, seq)
        if key in self._seen:
            return
        self._seen.add(key)
        self._order.append(key)
        if len(self._order) > self._max_entries:
            evicted = self._order.popleft()
            self._seen.discard(evicted)
