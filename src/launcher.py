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
KeyBridge launcher — the double-click desktop experience.

A small window guides first-run pairing (status, a scannable QR, where to get the app,
a same-Wi-Fi hint, and trouble-connecting help). Once a phone is connected it recedes to
the system tray; closing the window minimises there rather than stopping the bridge. The
tray icon reflects whether a device is connected — so you can always tell, at a glance,
whether something can type on this PC.
"""

import sys
import threading

from PySide6 import QtCore, QtGui, QtWidgets

from server import KeyBridgeServer
from utils.logger import setup_logger

logger = setup_logger()

APP_NAME = "KeyBridge"
SINGLE_INSTANCE_KEY = "keybridge-launcher-single-instance"

# Status accents as (light-theme, dark-theme) pairs — each chosen to keep good contrast
# against that theme's window background. Meaning is also carried by text + icon shape,
# never colour alone.
_ACCENTS = {
    "waiting": ("#1565c0", "#64b5f6"),
    "connected": ("#2e7d32", "#66bb6a"),
    "off": ("#6d6d6d", "#9e9e9e"),
    "error": ("#c62828", "#ef9a9a"),
}


def palette_is_dark(palette: QtGui.QPalette) -> bool:
    return palette.color(QtGui.QPalette.Window).lightnessF() < 0.5


def accent(name: str, dark: bool) -> QtGui.QColor:
    light_hex, dark_hex = _ACCENTS[name]
    return QtGui.QColor(dark_hex if dark else light_hex)


def blend(a: QtGui.QColor, b: QtGui.QColor, t: float) -> QtGui.QColor:
    """Blend a toward b by fraction t (0..1)."""
    return QtGui.QColor(
        round(a.red() * (1 - t) + b.red() * t),
        round(a.green() * (1 - t) + b.green() * t),
        round(a.blue() * (1 - t) + b.blue() * t),
    )


def make_icon(colour: QtGui.QColor, filled: bool) -> QtGui.QIcon:
    """A simple keyboard-key glyph in the status colour; 'filled' marks a connected device."""
    size = 64
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(QtGui.QPen(colour, 4))
    painter.setBrush(colour if filled else QtCore.Qt.transparent)
    painter.drawRoundedRect(8, 14, 48, 36, 8, 8)
    # Three "keys" so the glyph reads as a keyboard even in monochrome.
    painter.setPen(QtGui.QPen(QtCore.Qt.white if filled else colour, 4))
    for x in (20, 32, 44):
        painter.drawPoint(x, 32)
    painter.end()
    return QtGui.QIcon(pixmap)


class ServerSignals(QtCore.QObject):
    """Bridges the server thread to the GUI thread (Qt signals are queued across threads)."""
    clientsChanged = QtCore.Signal(int)
    errorOccurred = QtCore.Signal(str)


class LauncherWindow(QtWidgets.QWidget):
    def __init__(self, server: KeyBridgeServer) -> None:
        super().__init__()
        self.server = server
        self._allow_close = False  # set true only on a real Quit
        self._state = "waiting"    # waiting | connected | error
        self._error_text = ""
        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(440)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        self.title = QtWidgets.QLabel(APP_NAME)
        self.title.setStyleSheet("font-size: 22px; font-weight: 600;")
        root.addWidget(self.title)

        # Status line: a coloured dot + plain-language text (the text carries the meaning).
        status_row = QtWidgets.QHBoxLayout()
        self._dot = QtWidgets.QLabel()
        self._dot.setFixedSize(12, 12)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        status_row.addWidget(self._dot)
        status_row.addSpacing(8)
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        root.addLayout(status_row)

        # The QR sits on its own white card (its quiet zone), so it always has the light,
        # high-contrast surface a QR needs — independent of the window's light/dark theme.
        self.qr_card = QtWidgets.QFrame()
        self.qr_card.setStyleSheet("QFrame { background: #ffffff; border-radius: 14px; }")
        card_layout = QtWidgets.QVBoxLayout(self.qr_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        self.qr_label = QtWidgets.QLabel()
        self.qr_label.setAlignment(QtCore.Qt.AlignCenter)
        self.qr_label.setAccessibleName("Pairing QR code")
        pix = QtGui.QPixmap(self.server.qr_path)
        if not pix.isNull():
            self.qr_label.setPixmap(
                pix.scaled(260, 260, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
            )
        card_layout.addWidget(self.qr_label)
        qr_row = QtWidgets.QHBoxLayout()
        qr_row.addStretch(1)
        qr_row.addWidget(self.qr_card)
        qr_row.addStretch(1)
        root.addLayout(qr_row)

        self.qr_caption = QtWidgets.QLabel("Open the KeyBridge app on your phone and scan this code.")
        self.qr_caption.setWordWrap(True)
        self.qr_caption.setAlignment(QtCore.Qt.AlignCenter)
        root.addWidget(self.qr_caption)

        # Connected / error panel (shown instead of the QR).
        self.message_label = QtWidgets.QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(QtCore.Qt.AlignCenter)
        self.message_label.setStyleSheet("font-size: 15px;")
        self.message_label.hide()
        root.addWidget(self.message_label)

        # Same-Wi-Fi hint + manual address.
        self.hint = QtWidgets.QLabel(
            "Your phone must be on the same Wi-Fi network as this PC.\n"
            f"Address: {self.server.pairing_url}"
        )
        self.hint.setWordWrap(True)
        root.addWidget(self.hint)

        # Trouble-connecting help — the firewall is the top real-world failure.
        self.help_box = QtWidgets.QLabel(
            "Phone won't connect? Make sure both devices are on the same Wi-Fi, and "
            "allow KeyBridge through Windows Firewall when prompted."
        )
        self.help_box.setWordWrap(True)
        self.help_box.setStyleSheet("font-size: 12px;")
        root.addWidget(self.help_box)

        # Actions.
        buttons = QtWidgets.QHBoxLayout()
        copy_btn = QtWidgets.QPushButton("Copy connection details")
        copy_btn.setToolTip("Copy the pairing details to share another way if you can't scan.")
        copy_btn.clicked.connect(self._copy_details)
        hide_btn = QtWidgets.QPushButton("Hide to tray")
        hide_btn.clicked.connect(self.hide)
        buttons.addWidget(copy_btn)
        buttons.addStretch(1)
        buttons.addWidget(hide_btn)
        root.addLayout(buttons)

        self.update_status(self.server.client_count)

    def _muted(self) -> QtGui.QColor:
        """A de-emphasised but still readable text colour for the current theme."""
        pal = self.palette()
        return blend(pal.color(QtGui.QPalette.WindowText), pal.color(QtGui.QPalette.Window), 0.35)

    def _apply_theme(self) -> None:
        dark = palette_is_dark(self.palette())
        muted = self._muted()
        for label in (self.hint, self.help_box):
            size = "12px" if label is self.help_box else "13px"
            label.setStyleSheet(f"color: {muted.name()}; font-size: {size};")
        # Status colour (dot + text) per current state and theme.
        name = {"waiting": "waiting", "connected": "connected", "error": "off"}[self._state]
        colour = accent(name, dark)
        self._dot.setStyleSheet(f"background-color: {colour.name()}; border-radius: 6px;")
        self.status_label.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {colour.name()};")
        if self._state == "error":
            self.message_label.setStyleSheet(f"font-size: 15px; color: {accent('error', dark).name()};")
        else:
            self.message_label.setStyleSheet("font-size: 15px;")

    def changeEvent(self, event: QtCore.QEvent) -> None:
        # Re-theme live when the OS switches between light and dark.
        if event.type() in (QtCore.QEvent.PaletteChange, QtCore.QEvent.ApplicationPaletteChange):
            self._apply_theme()
        super().changeEvent(event)

    def _copy_details(self) -> None:
        QtWidgets.QApplication.clipboard().setText(self.server.connection_string)
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), "Copied", self)

    def update_status(self, client_count: int) -> None:
        connected = client_count > 0
        self._state = "connected" if connected else "waiting"
        if connected:
            self.status_label.setText("Phone connected")
            self.qr_card.hide()
            self.qr_caption.hide()
            self.message_label.setText("Your phone is connected — start typing.")
            self.message_label.show()
        else:
            self.status_label.setText("Ready to pair")
            self.message_label.hide()
            self.qr_card.show()
            self.qr_caption.show()
        self.status_label.setAccessibleName(f"Status: {self.status_label.text()}")
        self._apply_theme()

    def update_error(self, message: str) -> None:
        self._state = "error"
        self._error_text = message
        self.status_label.setText("Not running")
        self.status_label.setAccessibleName("Status: not running")
        self.qr_card.hide()
        self.qr_caption.hide()
        self.message_label.setText(message)
        self.message_label.show()
        self._apply_theme()

    def request_quit(self) -> None:
        self._allow_close = True
        self.close()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        # Closing the window hides to the tray; it must not silently stop the bridge.
        if self._allow_close:
            event.accept()
            return
        event.ignore()
        self.hide()


class LauncherApp:
    def __init__(self) -> None:
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setApplicationName(APP_NAME)
        self.app.setQuitOnLastWindowClosed(False)  # closing the window keeps us in the tray

        self.signals = ServerSignals()
        self.server = KeyBridgeServer(
            on_clients_changed=self.signals.clientsChanged.emit,
            on_error=self.signals.errorOccurred.emit,
        )
        self.window = LauncherWindow(self.server)
        self.signals.clientsChanged.connect(self._on_clients_changed)
        self.signals.errorOccurred.connect(self._on_error)

        self.tray = QtWidgets.QSystemTrayIcon(self._tray_icon("waiting", filled=False), self.app)
        self.tray.setToolTip(f"{APP_NAME} — waiting to pair")
        menu = QtWidgets.QMenu()
        show_action = menu.addAction("Show KeyBridge")
        show_action.triggered.connect(self._show_window)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.window.request_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        self._server_thread = threading.Thread(target=self.server.run, name="keybridge-server", daemon=True)
        self._first_hide_notice_shown = False

    def _tray_icon(self, name: str, filled: bool) -> QtGui.QIcon:
        return make_icon(accent(name, palette_is_dark(self.app.palette())), filled)

    def _on_tray_activated(self, reason) -> None:
        if reason == QtWidgets.QSystemTrayIcon.Trigger:  # left click
            self._show_window()

    def _show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _on_clients_changed(self, count: int) -> None:
        self.window.update_status(count)
        connected = count > 0
        self.tray.setIcon(self._tray_icon("connected" if connected else "waiting", filled=connected))
        self.tray.setToolTip(f"{APP_NAME} — {'phone connected' if connected else 'waiting to pair'}")

    def _on_error(self, message: str) -> None:
        self.window.update_error(message)
        self.tray.setIcon(self._tray_icon("off", filled=False))
        self.tray.setToolTip(f"{APP_NAME} — not running")
        self._show_window()  # bring the problem to the user's attention

    def notify_hidden_to_tray(self) -> None:
        if not self._first_hide_notice_shown and QtWidgets.QSystemTrayIcon.supportsMessages():
            self._first_hide_notice_shown = True
            self.tray.showMessage(
                APP_NAME, "Still running here. Click the tray icon to show it again.",
                QtWidgets.QSystemTrayIcon.Information, 4000,
            )

    def run(self) -> int:
        self._server_thread.start()
        self.window.show()
        self.window.installEventFilter(_HideNotifier(self))
        code = self.app.exec()
        self.server.stop()
        self._server_thread.join(timeout=3)
        return code


class _HideNotifier(QtCore.QObject):
    """Shows the one-time 'still running in the tray' notice the first time the window hides."""

    def __init__(self, launcher: "LauncherApp") -> None:
        super().__init__()
        self._launcher = launcher

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QtCore.QEvent.Hide and not obj.isMinimized():
            self._launcher.notify_hidden_to_tray()
        return False


def main() -> int:
    # Single instance: a second launch should not start a second server. QLockFile is
    # QtCore-only, so it is safe before a QApplication exists. A 30s stale time lets a
    # crashed instance's lock be reclaimed.
    lock = QtCore.QLockFile(QtCore.QDir.tempPath() + f"/{SINGLE_INSTANCE_KEY}.lock")
    lock.setStaleLockTime(30000)
    if not lock.tryLock(100):
        logger.info("KeyBridge is already running")
        return 0

    # LauncherApp creates the QApplication. QtWidgets statics (e.g. isSystemTrayAvailable)
    # must not be called before it exists — doing so crashes the Windows platform plugin.
    launcher = LauncherApp()
    if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
        logger.warning("No system tray available; the window stays open instead")
    return launcher.run()


if __name__ == "__main__":
    sys.exit(main())
