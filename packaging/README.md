# Packaging the KeyBridge host (Windows)

Produces a double-click desktop app — no Python required on the target machine.

## 1. Build the app bundle (PyInstaller)

From the repo root, with the dev dependencies installed (`pip install -r requirements-dev.txt`):

```bat
pyinstaller packaging\keybridge.spec
```

This creates a self-contained folder **`dist\KeyBridge\`** containing `KeyBridge.exe`.
You can run it directly (`dist\KeyBridge\KeyBridge.exe`) to test — it bundles Python, Qt,
and all dependencies. The app writes its logs and QR image to `%LOCALAPPDATA%\KeyBridge`,
so it never needs write access to its own folder.

## 2. Build the installer (Inno Setup)

Install [Inno Setup 6](https://jrsoftware.org/isinfo.php), then:

```bat
iscc packaging\keybridge.iss
```

This produces **`packaging\Output\KeyBridge-Setup.exe`** — a per-user installer (no admin
prompt) that adds Start-menu and (optional) desktop shortcuts and registers an uninstaller.
"Start automatically when I sign in" is offered inside the app (Options menu), not the
installer.

## Notes

- **SmartScreen:** an unsigned build may show a "Windows protected your PC" prompt on first
  run — choose *More info → Run anyway*. Code signing removes this (not configured here).
- The bundle is large because it includes the Qt runtime; that is expected.
- Running from source still works for development: `python src\launcher.py` (or `main.py`
  for the headless server).
