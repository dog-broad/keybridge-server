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

import logging
import os
import sys
import threading

from PySide6 import QtCore, QtGui, QtWidgets

from server import KeyBridgeServer
from utils.logger import setup_logger
from utils.paths import logs_dir

try:
    import winreg  # Windows only; autostart is a no-op elsewhere
except ImportError:
    winreg = None

logger = setup_logger()

APP_NAME = "KeyBridge"
SINGLE_INSTANCE_KEY = "keybridge-launcher-single-instance"
_AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def open_logs_folder() -> None:
    QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(logs_dir()))


def set_verbose_logging(enabled: bool) -> None:
    """Raise/lower the log level at runtime (the file handler already accepts DEBUG)."""
    logging.getLogger("keybridge").setLevel(logging.DEBUG if enabled else logging.INFO)


def _autostart_command() -> str:
    """The command Windows should run at sign-in to relaunch the launcher."""
    if getattr(sys, "frozen", False):  # packaged exe
        return f'"{sys.executable}"'
    # From source: prefer the windowless interpreter so no console flashes at sign-in.
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pythonw if os.path.exists(pythonw) else sys.executable
    return f'"{exe}" "{os.path.abspath(__file__)}"'


def is_autostart_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _AUTOSTART_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled: bool) -> bool:
    """Enable/disable launch at sign-in. Returns the resulting state."""
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except OSError:
                    pass
        return enabled
    except OSError as e:
        logger.error(f"Could not update autostart: {e}")
        return is_autostart_enabled()

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


class LauncherWindow(QtWidgets.QMainWindow):
    def __init__(self, server: KeyBridgeServer) -> None:
        super().__init__()
        self.server = server
        self._quitting = False  # true only when really exiting (menu / dialog Quit)
        self._settings = QtCore.QSettings(APP_NAME, "Launcher")
        self._state = "waiting"    # waiting | connected | error
        self._error_text = ""
        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(440)

        self._build_menus()

        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(28, 20, 28, 24)
        root.setSpacing(16)

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

        self.setCentralWidget(central)
        self.update_status(self.server.client_count)

    def _build_menus(self) -> None:
        """A conventional menu bar — the standard, app-like home for secondary actions.

        Items carry native icons so the menu's fixed icon/checkmark gutter reads as
        'icon + text' (as in most apps) rather than empty space before each label.
        """
        style = self.style()
        SP = QtWidgets.QStyle.StandardPixmap
        bar = self.menuBar()

        file_menu = bar.addMenu("&File")
        file_menu.addAction(style.standardIcon(SP.SP_TitleBarMinButton), "Hide to Tray", self.hide)
        file_menu.addSeparator()
        file_menu.addAction(style.standardIcon(SP.SP_DialogCloseButton), "Quit", self.request_quit)

        tools = bar.addMenu("&Tools")
        tools.addAction(style.standardIcon(SP.SP_BrowserReload), "Regenerate Pairing Code…", self._regenerate)
        tools.addAction(style.standardIcon(SP.SP_DirOpenIcon), "Open Logs Folder", open_logs_folder)
        tools.addAction(style.standardIcon(SP.SP_FileDialogDetailedView), "Copy Connection Details", self._copy_details)

        options = bar.addMenu("&Options")
        self.autostart_action = options.addAction(
            style.standardIcon(SP.SP_ComputerIcon), "Start Automatically When I Sign In"
        )
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(is_autostart_enabled())
        self.autostart_action.toggled.connect(self._on_autostart_toggled)
        if winreg is None:
            self.autostart_action.setEnabled(False)
        self.verbose_action = options.addAction(
            style.standardIcon(SP.SP_FileIcon), "Verbose Logging (for troubleshooting)"
        )
        self.verbose_action.setCheckable(True)
        self.verbose_action.toggled.connect(set_verbose_logging)

        options.addSeparator()
        close_menu = options.addMenu("When I Close the Window")
        self._close_group = QtGui.QActionGroup(self)
        self._close_group.setExclusive(True)
        for label, value in (("Ask Me Each Time", "ask"), ("Minimize to Tray", "tray"), ("Quit", "quit")):
            act = close_menu.addAction(label)
            act.setCheckable(True)
            act.setData(value)
            act.setChecked(self._close_behavior() == value)
            self._close_group.addAction(act)
        self._close_group.triggered.connect(lambda a: self._set_close_behavior(a.data()))

        help_menu = bar.addMenu("&Help")
        help_menu.addAction(style.standardIcon(SP.SP_MessageBoxInformation), "About KeyBridge", self._about)

    def _about(self) -> None:
        QtWidgets.QMessageBox.about(
            self, "About KeyBridge",
            "KeyBridge turns your phone into a keyboard for this PC.\n\n"
            "Scan the QR code with the KeyBridge app, on the same Wi-Fi network, to pair. "
            "The pairing key travels only in the QR — never over the network.",
        )

    def _on_autostart_toggled(self, enabled: bool) -> None:
        result = set_autostart(enabled)
        if result != enabled:  # the write failed; reflect the real state without re-triggering
            self.autostart_action.blockSignals(True)
            self.autostart_action.setChecked(result)
            self.autostart_action.blockSignals(False)

    def reload_qr(self) -> None:
        # Load via QImage to bypass any pixmap cache after the QR file is rewritten.
        image = QtGui.QImage(self.server.qr_path)
        if not image.isNull():
            self.qr_label.setPixmap(
                QtGui.QPixmap.fromImage(image).scaled(
                    260, 260, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation
                )
            )

    def _regenerate(self) -> None:
        self.server.regenerate_pairing()
        self.reload_qr()
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), "New code generated — rescan on your phone", self)

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

    def _close_behavior(self) -> str:
        return self._settings.value("closeBehavior", "ask")

    def _set_close_behavior(self, value: str) -> None:
        self._settings.setValue("closeBehavior", value)
        for act in self._close_group.actions():
            if act.data() == value:
                act.setChecked(True)

    def request_quit(self) -> None:
        # Really exit. quitOnLastWindowClosed is False (we live in the tray), so closing the
        # window alone won't end the app — we must quit the application explicitly.
        self._quitting = True
        QtWidgets.QApplication.quit()

    def _minimize_to_tray(self, event: QtGui.QCloseEvent) -> None:
        event.ignore()
        self.hide()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._quitting:
            event.accept()
            return

        behavior = self._close_behavior()
        if behavior == "tray":
            self._minimize_to_tray(event)
            return
        if behavior == "quit":
            event.ignore()
            self.request_quit()
            return

        # Ask, and optionally remember the choice. Minimizing is the default (it's a
        # background bridge); the X should never silently stop it without a say.
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("Close KeyBridge")
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setText("KeyBridge can keep running in the background so your phone stays paired.")
        box.setInformativeText("Minimize to the tray, or quit completely?")
        tray_btn = box.addButton("Minimize to Tray", QtWidgets.QMessageBox.AcceptRole)
        quit_btn = box.addButton("Quit", QtWidgets.QMessageBox.DestructiveRole)
        box.setDefaultButton(tray_btn)
        remember = QtWidgets.QCheckBox("Remember my choice")
        box.setCheckBox(remember)
        box.exec()

        if box.clickedButton() is quit_btn:
            if remember.isChecked():
                self._set_close_behavior("quit")
            event.ignore()
            self.request_quit()
        else:  # Minimize to tray (also the default if the dialog is dismissed)
            if remember.isChecked():
                self._set_close_behavior("tray")
            self._minimize_to_tray(event)


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

    def run(self) -> int:
        self._server_thread.start()
        self.window.show()
        code = self.app.exec()
        self.server.stop()
        self._server_thread.join(timeout=3)
        return code


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
