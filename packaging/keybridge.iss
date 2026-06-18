; Inno Setup script for the KeyBridge installer.
; Build the bundle first (pyinstaller packaging/keybridge.spec), then compile this with
; Inno Setup 6:  iscc packaging\keybridge.iss   ->  packaging\Output\KeyBridge-Setup.exe
;
; Per-user install (no admin prompt). The app writes logs/QR to %LOCALAPPDATA%\KeyBridge,
; so it never needs write access to its install folder.

#define AppName "KeyBridge"
#define AppVersion "1.1.0"
#define AppExe "KeyBridge.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Rushyendra Guntupalli (dog-broad) and Contributors
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\src\assets\keybridge.ico
OutputDir=Output
OutputBaseFilename={#AppName}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\dist\KeyBridge\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent
