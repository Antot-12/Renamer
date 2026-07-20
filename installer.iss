; Inno Setup Script for Renamer
; Download Inno Setup from: https://jrsoftware.org/isinfo.php
;
; To build installer:
; 1. Install Inno Setup
; 2. Run: iscc installer.iss
; Or open this file in Inno Setup and click Build

#define MyAppName "Renamer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Antot"
#define MyAppURL "https://github.com/Antot-12/Renamer"
#define MyAppExeName "Renamer.exe"

[Setup]
; App identification
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Installation directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output settings
OutputDir=installer_output
OutputBaseFilename=Renamer-Setup-{#MyAppVersion}
SetupIconFile=ico.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Modern look
WizardStyle=modern
WizardSizePercent=100

; Privileges (per-user by default, can elevate)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Misc
AllowNoIcons=yes
DisableWelcomePage=no
ShowLanguageDialog=auto

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "contextmenu"; Description: "Add 'Rename with Renamer' to context menu"; GroupDescription: "Windows Integration:"; Flags: unchecked
Name: "foldercontextmenu"; Description: "Add 'Rename files with Renamer' to folder context menu"; GroupDescription: "Windows Integration:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "ico.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
; Add any additional data files here

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; File context menu - "Rename with Renamer"
Root: HKCR; Subkey: "*\shell\RenameWithRenamer"; ValueType: string; ValueName: ""; ValueData: "Rename with Renamer"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCR; Subkey: "*\shell\RenameWithRenamer"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"; Tasks: contextmenu
Root: HKCR; Subkey: "*\shell\RenameWithRenamer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: contextmenu

; Folder context menu - "Rename files with Renamer"
Root: HKCR; Subkey: "Directory\shell\RenameWithRenamer"; ValueType: string; ValueName: ""; ValueData: "Rename files with Renamer"; Tasks: foldercontextmenu; Flags: uninsdeletekey
Root: HKCR; Subkey: "Directory\shell\RenameWithRenamer"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"; Tasks: foldercontextmenu
Root: HKCR; Subkey: "Directory\shell\RenameWithRenamer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: foldercontextmenu

; Directory background context menu (right-click in empty area)
Root: HKCR; Subkey: "Directory\Background\shell\RenameWithRenamer"; ValueType: string; ValueName: ""; ValueData: "Rename files with Renamer"; Tasks: foldercontextmenu; Flags: uninsdeletekey
Root: HKCR; Subkey: "Directory\Background\shell\RenameWithRenamer"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"; Tasks: foldercontextmenu
Root: HKCR; Subkey: "Directory\Background\shell\RenameWithRenamer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%V"""; Tasks: foldercontextmenu

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Check if .NET or other dependencies are needed (placeholder)
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// Custom uninstall cleanup
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Clean up any leftover user data if desired
    // DelTree(ExpandConstant('{userappdata}\Renamer'), True, True, True);
  end;
end;
