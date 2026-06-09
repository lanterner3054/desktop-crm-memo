; Inno Setup script for 客户跟进 (Customer Follow-up)
; Builds a per-user installer (no admin/UAC prompt for recipients).

#define MyAppName "客户跟进"
#ifndef MyAppVersion
  #define MyAppVersion "1.0"
#endif
#define MyAppPublisher "lanterner3054"
#define MyAppExeName "DesktopMemo.exe"

[Setup]
AppId={{8F3A2C71-4D5E-4B90-9C12-CFA7E6B10001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; per-user install -> no administrator rights needed
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_out
OutputBaseFilename=desktop-crm-memo-setup-v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; UI language
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: checkedonce

[Files]
; bundle the whole PyInstaller onedir output
Source: "dist\DesktopMemo\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent
