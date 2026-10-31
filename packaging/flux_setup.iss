; Flux Storage (MTR Soft) setup script - Inno Setup 6
; Source builds from the PyInstaller one-dir distribution in ..\dist\FluxStorage.
; Per-user by default (no UAC for Commerce prompt); machine-wide requires an explicit choice.
; Personal data in %LOCALAPPDATA%\FluxStorage is preserved; purge needs an explicit answer.

#define ProductName "Flux Storage"
#define Publisher "MTR Soft"
#define AppVersion "2.2.0"
#define ExeName "FluxStorage"
#define AppId "654C1AF9-D7DF-45FD-BBAA-34BB40A552E4"

[Setup]
AppId={#AppId}
AppName={#ProductName} ({#Publisher})
AppVersion={#AppVersion}
VersionInfoVersion=2.2.0.1
AppPublisher={#Publisher}
AppPublisherURL=https://github.com/mtrakretech/flux-storage
AppReadmeFile=https://github.com/mtrakretech/flux-storage#readme
AppSupportURL=https://github.com/mtrakretech/flux-storage/issues
DefaultDirName={autopf}\{#ProductName}
DirExistsWarning=no
DefaultGroupName={#ProductName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist\setup
OutputBaseFilename=FluxStorage-{#AppVersion}-setup
SetupIconFile=flux.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
Uninstallable=yes
UninstallDisplayName={#ProductName} ({#Publisher})
UninstallDisplayIcon={app}\{#ExeName}.exe
CloseApplications=yes
ChangesAssociations=no
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkablealone

[Files]
Source: "..\dist\FluxStorage\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#ProductName}"; Filename: "{app}\{#ExeName}.exe"; Comment: "{#ProductName} by {#Publisher} - local drive inventory and cleanup"
Name: "{autodesktop}\{#ProductName}"; Filename: "{app}\{#ExeName}.exe"; Comment: "{#ProductName} by {#Publisher}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}.exe"; Description: "{cm:LaunchProgram,{#ProductName}}"; Flags: nowait postinstall skipifsilent skipifnotsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: string;
begin
  if CurUninstallStep = usUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}') + '\FluxStorage';
    if DirExists(DataDir) then
      if MsgBox('Keep your Flux Storage snapshots, settings and history in' + #13#10 +
                DataDir + '?' + #13#10#13#10 +
                'Choose Yes to keep them (recommended). Choose No to delete them from this PC.',
                mbConfirmation, MB_YESNO) = IDNO then
        DelTree(DataDir, True, True, True);
  end;
end;
