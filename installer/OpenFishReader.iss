#define MyAppName "Open Fish Reader"
#ifndef MyAppVersion
  #define MyAppVersion "0.9.0"
#endif
#ifndef MyAppPublisher
  #define MyAppPublisher "Open Fish Reader"
#endif
#define MyAppExeName "OpenFishReader.exe"
[Setup]
AppId={{D0FC4165-8811-4D18-8DFC-A7A448C84E89}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Open Fish Reader
DefaultGroupName=Open Fish Reader
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\installer_output
OutputBaseFilename=OpenFishReader-{#MyAppVersion}-Setup
SetupIconFile=..\src\open_fish_reader\resources\icons\open_fish_reader.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le bureau"; GroupDescription: "Raccourcis supplémentaires :"; Flags: unchecked
[Files]
Source: "..\dist\Open Fish Reader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\Open Fish Reader"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Open Fish Reader"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer Open Fish Reader"; Flags: nowait postinstall skipifsilent
