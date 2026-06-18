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
Writable paths for runtime files (logs, the generated QR image).

A packaged install lives in read-only Program Files, so when frozen we write to the
user's local app-data folder. Run from source, we keep using the working directory so
the developer flow is unchanged.
"""

import os
import sys

APP_DIR_NAME = "KeyBridge"


def app_data_dir() -> str:
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = os.path.join(base, APP_DIR_NAME)
    else:
        path = os.getcwd()
    os.makedirs(path, exist_ok=True)
    return path


def logs_dir() -> str:
    path = os.path.join(app_data_dir(), "logs")
    os.makedirs(path, exist_ok=True)
    return path


def qr_image_path() -> str:
    return os.path.join(app_data_dir(), "connection_qr.png")


def resource_path(*parts: str) -> str:
    """Absolute path to a bundled read-only resource (e.g. the app icon).

    When frozen, PyInstaller unpacks data files under ``sys._MEIPASS``; from source we
    resolve relative to the ``src`` directory. So ``resource_path("assets", "keybridge.png")``
    works in both flows.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)
