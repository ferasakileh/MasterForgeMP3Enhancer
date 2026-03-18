; Inno Setup installer script for MasterForge 320
; Build command example:
;   iscc /DMyAppVersion=1.0.0 /DMyAppSourceDir="C:\path\to\dist\MasterForge320" /DMyOutputDir="C:\path\to\dist" installer\MasterForge320.iss

#define MyAppName "MasterForge 320"
#define MyAppPublisher "MasterForge Audio"
#define MyAppURL "https://github.com/ferasakileh"
#define MyAppExeName "MasterForge320.exe"

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#ifndef MyAppSourceDir
  #define MyAppSourceDir "dist\\MasterForge320"
#endif

#ifndef MyOutputDir
  #define MyOutputDir "dist"
#endif

[Setup]
AppId={{F6EC3783-4E3D-4A56-8AD9-0C64E6608A6E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\MasterForge320
DefaultGroupName=MasterForge 320
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
OutputDir={#MyOutputDir}
OutputBaseFilename=MasterForge320-Setup-{#MyAppVersion}-x64
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MasterForge 320"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\MasterForge 320"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch MasterForge 320"; Flags: nowait postinstall skipifsilent
