# PyInstaller spec for the KeyBridge launcher — a windowed, one-folder Windows bundle.
# Build:  pyinstaller packaging/keybridge.spec
# Output: dist/KeyBridge/KeyBridge.exe  (self-contained; no Python needed to run).

import os

# Resolve paths relative to this spec file, so the build works from any working directory.
_SRC = os.path.join(os.path.abspath(os.path.join(SPECPATH, "..")), "src")
_ICON = os.path.join(_SRC, "assets", "keybridge.ico")

a = Analysis(
    [os.path.join(_SRC, "launcher.py")],
    pathex=[_SRC],
    binaries=[],
    # Bundle the brand icon so the window/taskbar can load it at runtime.
    datas=[(os.path.join(_SRC, "assets"), "assets")],
    # pynput loads its OS backend lazily, and qrcode imports its Pillow image factory
    # lazily — PyInstaller can miss both without hints.
    hiddenimports=["pynput.keyboard._win32", "pynput.mouse._win32", "PIL", "qrcode.image.pil"],
    hookspath=[],
    runtime_hooks=[],
    # Trim large Qt modules the launcher never uses, to keep the bundle smaller.
    excludes=[
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtNetwork", "PySide6.QtWebEngineCore",
        "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtTest",
        "tkinter",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KeyBridge",
    debug=False,
    strip=False,
    upx=False,
    console=False,            # windowed: no console flashes at launch
    icon=_ICON,               # brand icon on the .exe
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="KeyBridge",
)
