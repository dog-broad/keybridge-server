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
Message Handler Module

Routes a parsed input envelope to the keyboard controller and returns the
acknowledgement for that chunk. Typing and key simulation run in a worker thread
so a long or delayed chunk never blocks the event loop that must deliver the ack.
"""

import asyncio
from typing import Any, Dict, List

from .logger import get_logger
from .keyboard_controller import KeyboardController
from .commands import CommandValidator
from .envelope import Envelope, EnvelopeType, SeenChunks, build_ack

logger = get_logger(__name__)


class MessageHandler:
    """Applies input envelopes and acknowledges each applied chunk."""

    def __init__(self) -> None:
        """Initialize the message handler with the singleton keyboard controller."""
        self.keyboard = KeyboardController()

    async def handle_envelope(self, envelope: Envelope, seen: SeenChunks) -> Dict[str, Any]:
        """
        Apply one input chunk and return its acknowledgement.

        A chunk whose ``(id, seq)`` was already applied on this connection is re-acked
        without being applied again, so a client may safely resend a chunk whose ack
        was lost. A payload that fails validation or application is acked as an error
        and not recorded as applied, so a corrected resend is still processed.
        """
        if seen.has(envelope.id, envelope.seq):
            logger.debug(f"Duplicate chunk {envelope.id}#{envelope.seq}; re-acking without applying")
            return build_ack(envelope.id, envelope.seq, "ok")

        try:
            CommandValidator.validate_payload(envelope.type, envelope.payload)
            await self._apply(envelope)
        except Exception as e:
            logger.error(f"Failed to apply chunk {envelope.id}#{envelope.seq}: {e}")
            return build_ack(envelope.id, envelope.seq, "error", str(e))

        seen.add(envelope.id, envelope.seq)
        return build_ack(envelope.id, envelope.seq, "ok")

    async def _apply(self, envelope: Envelope) -> None:
        """Apply the envelope's input off the event loop, preserving order per message."""
        loop = asyncio.get_running_loop()
        payload = envelope.payload

        if envelope.type == EnvelopeType.TYPE:
            text = payload["text"]
            delay_ms = payload.get("delay_ms", 0)
            await loop.run_in_executor(None, self.keyboard.type_text, text, delay_ms)
        elif envelope.type == EnvelopeType.KEY_PRESS:
            await loop.run_in_executor(None, self.keyboard.press_key, payload["key"])
        elif envelope.type == EnvelopeType.KEY_RELEASE:
            await loop.run_in_executor(None, self.keyboard.release_key, payload["key"])
        elif envelope.type == EnvelopeType.KEY_COMBO:
            await loop.run_in_executor(None, self._apply_combo, payload["keys"])
        else:
            # Validation rejects non-input types before reaching here.
            raise ValueError(f"Cannot apply envelope type: {envelope.type.value}")

    def _apply_combo(self, keys: List[str]) -> None:
        """Press the keys in order, then release them in reverse order."""
        for key in keys:
            self.keyboard.press_key(key)
        for key in reversed(keys):
            self.keyboard.release_key(key)
