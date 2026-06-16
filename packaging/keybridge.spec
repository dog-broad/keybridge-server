# PyInstaller spec for the KeyBridge launcher — a windowed, one-folder Windows bundle.
# Build:  pyinstaller packaging/keybridge.spec
# Output: dist/KeyBridge/KeyBridge.exe  (self-contained; no Python needed to run).

import os

# Resolve paths relative to this spec file, so the build works from any working directory.
_SRC = os.path.join(os.path.abspath(os.path.join(SPECPATH, "..")), "src")

a = Analysis(
    [os.path.join(_SRC, "launcher.py")],
    pathex=[_SRC],
    binaries=[],
    datas=[],
    # pynput loads its OS backend lazily, so PyInstaller can miss it without a hint.
    hiddenimports=["pynput.keyboard._win32", "pynput.mouse._win32"],
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="KeyBridge",
)
