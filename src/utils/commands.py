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
Commands Module

This module owns the set of supported keys and validates the payload of each
envelope input type before it is applied. Envelope structure (version, id, seq,
total, type) is validated in ``envelope.py``; this module validates the body.
"""

from typing import Dict, Any
from pynput.keyboard import Key

from .envelope import EnvelopeType

# Key mapping from string names to pynput Key enum values (same as in KeyboardController)
# Includes cross-platform aliases for Windows, Mac, and Linux
SUPPORTED_KEYS = {
    # Navigation keys
    'backspace': Key.backspace,
    'tab': Key.tab,
    'enter': Key.enter,
    'return': Key.enter,      # Mac alias
    'shift': Key.shift,
    'ctrl': Key.ctrl,
    'control': Key.ctrl,      # Mac alias
    'alt': Key.alt,
    'option': Key.alt,        # Mac alias - Option key is Alt
    'opt': Key.alt,           # Mac alias
    'space': Key.space,
    'esc': Key.esc,
    'escape': Key.esc,
    
    # Arrow keys
    'up': Key.up,
    'down': Key.down,
    'left': Key.left,
    'right': Key.right,
    
    # Function keys
    'f1': Key.f1,
    'f2': Key.f2,
    'f3': Key.f3,
    'f4': Key.f4,
    'f5': Key.f5,
    'f6': Key.f6,
    'f7': Key.f7,
    'f8': Key.f8,
    'f9': Key.f9,
    'f10': Key.f10,
    'f11': Key.f11,
    'f12': Key.f12,
    
    # Special keys
    'home': Key.home,
    'end': Key.end,
    'page_up': Key.page_up,
    'page_down': Key.page_down,
    'insert': Key.insert,
    'ins': Key.insert,
    'delete': Key.delete,
    'del': Key.delete,
    
    # Modifier keys - Command/Windows/Super
    'cmd': Key.cmd,
    'command': Key.cmd,
    'windows': Key.cmd,
    'win': Key.cmd,
    'super': Key.cmd,         # Linux alias
    'meta': Key.cmd,          # Generic alias
    
    # Media keys
    'media_play_pause': Key.media_play_pause,
    'media_volume_up': Key.media_volume_up,
    'media_volume_down': Key.media_volume_down,
    'media_volume_mute': Key.media_volume_mute,
    'media_next': Key.media_next,
    'media_previous': Key.media_previous,
    
    # Lock keys
    'num_lock': Key.num_lock,
    'numlock': Key.num_lock,
    'scroll_lock': Key.scroll_lock,
    'scrolllock': Key.scroll_lock,
    'caps_lock': Key.caps_lock,
    'capslock': Key.caps_lock,
    
    # Print screen
    'print_screen': Key.print_screen,
    'prtsc': Key.print_screen,
    'prtscr': Key.print_screen,
    'printscreen': Key.print_screen,
    
    # Pause/Break
    'pause': Key.pause,
    'break': Key.pause,
    
    # Menu key
    'menu': Key.menu,
    'apps': Key.menu,
}

class CommandValidator:
    """Validates the payload of each envelope input type."""

    @staticmethod
    def validate_payload(env_type: EnvelopeType, payload: Dict[str, Any]) -> None:
        """
        Validate the payload for a given envelope input type.

        Args:
            env_type: The envelope type whose payload is being validated.
            payload: The envelope's payload object.

        Raises:
            ValueError: If the payload is missing fields, mistyped, or references an
                unsupported key. Acks are not a client-to-host input and are rejected.
        """
        if env_type == EnvelopeType.TYPE:
            CommandValidator._validate_type_payload(payload)
        elif env_type in (EnvelopeType.KEY_PRESS, EnvelopeType.KEY_RELEASE):
            CommandValidator._validate_key_payload(payload)
        elif env_type == EnvelopeType.KEY_COMBO:
            CommandValidator._validate_key_combo_payload(payload)
        else:
            raise ValueError(f"Cannot apply envelope type: {env_type.value}")

    @staticmethod
    def _validate_type_payload(payload: Dict[str, Any]) -> None:
        """Validate a 'type' payload: a non-empty string and an optional delay."""
        text = payload.get('text')
        if not isinstance(text, str):
            raise ValueError("'type' payload requires a string 'text' field")
        # Reject only a truly empty string. A chunk may legitimately be all whitespace
        # (a long run of spaces/newlines inside a larger paste); those are real characters
        # to type. Guarding against a blank *whole message* is the client's job.
        if text == "":
            raise ValueError("'text' cannot be empty")

        delay_ms = payload.get('delay_ms', 0)
        if not isinstance(delay_ms, int) or isinstance(delay_ms, bool) or delay_ms < 0:
            raise ValueError("'delay_ms' must be a non-negative integer")

    @staticmethod
    def _validate_key_payload(payload: Dict[str, Any]) -> None:
        """Validate a 'key_press'/'key_release' payload: one supported key."""
        key = payload.get('key')
        if not isinstance(key, str):
            raise ValueError("key payload requires a string 'key' field")
        if not CommandValidator._is_valid_key(key):
            raise ValueError(CommandValidator._unsupported_key_message(key))

    @staticmethod
    def _validate_key_combo_payload(payload: Dict[str, Any]) -> None:
        """Validate a 'key_combo' payload: a non-empty list of supported keys."""
        keys = payload.get('keys')
        if not isinstance(keys, list):
            raise ValueError("'key_combo' payload requires a 'keys' list")
        if not keys:
            raise ValueError("'keys' list cannot be empty")

        for i, key in enumerate(keys):
            if not isinstance(key, str):
                raise ValueError(f"All keys must be strings; key at index {i} is {type(key).__name__}")
            if not CommandValidator._is_valid_key(key):
                raise ValueError(CommandValidator._unsupported_key_message(key, index=i))

    @staticmethod
    def _is_valid_key(key_name: str) -> bool:
        """A key is valid if it is a supported special key or a single character."""
        key_name = key_name.lower().strip()
        if key_name in SUPPORTED_KEYS:
            return True
        return len(key_name) == 1

    @staticmethod
    def _unsupported_key_message(key: str, index: int = None) -> str:
        """Build a helpful 'unsupported key' message listing the supported names."""
        supported = ', '.join(sorted(SUPPORTED_KEYS.keys()))
        where = f" at index {index}" if index is not None else ""
        return (f"Unsupported key{where}: '{key}'. Supported: {supported} "
                f"or single characters (a-z, 0-9, symbols)")