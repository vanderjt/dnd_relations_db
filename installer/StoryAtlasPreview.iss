#ifndef AppVersion
#error AppVersion must be supplied from VERSION by build_preview_installer.ps1
#endif
[Setup]
; Keep this identity and per-user mode stable so updates reuse registration.
AppId={{B1A827F6-93A7-4365-A494-D793125179DA}
AppName=Story Atlas Preview
AppVersion={#AppVersion}
AppPublisher=Story Atlas
DefaultDirName={localappdata}\Programs\Story Atlas Preview
UsePreviousAppDir=yes
DefaultGroupName=Story Atlas Preview
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=.
OutputBaseFilename=StoryAtlasPreview-{#AppVersion}-Windows-x64-Offline-Setup
SetupIconFile=..\story_atlas\resources\story-atlas.ico
UninstallDisplayIcon={app}\StoryAtlasPreview.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\StoryAtlasPreview\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Install examples only once; user edits and all story data survive removal.
Source: "..\examples\saved-stories\*.atlas-preview"; DestDir: "{localappdata}\StoryAtlasPreview\stories"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "..\examples\saved-stories\portrait-sources.json"; DestDir: "{localappdata}\StoryAtlasPreview\stories"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "..\build\installer-deps\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; Flags: dontcopy

[Icons]
Name: "{userdesktop}\Story Atlas Preview"; Filename: "{app}\StoryAtlasPreview.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userprograms}\Story Atlas Preview"; Filename: "{app}\StoryAtlasPreview.exe"; WorkingDir: "{app}"
Name: "{userprograms}\Uninstall Story Atlas Preview"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\StoryAtlasPreview.exe"; Description: "Open Story Atlas Preview"; Flags: nowait postinstall skipifsilent

[Code]
function HasWebView2: Boolean;
var Version: String;
begin
  Result := (RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
  if not Result then
    Result := (RegQueryStringValue(HKLM32, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var ExitCode: Integer;
begin
  Result := '';
  if not HasWebView2 then begin
    ExtractTemporaryFile('MicrosoftEdgeWebView2RuntimeInstallerX64.exe');
    if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebView2RuntimeInstallerX64.exe'), '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
      Result := 'Unable to start the included offline WebView2 installer. Setup has not installed Story Atlas.'
    else if not HasWebView2 then
      Result := 'WebView2 installation did not complete (code ' + IntToStr(ExitCode) + '). Restart Windows if requested, then run this installer again.';
  end;
end;

// No uninstall-delete rule: user stories and backups are preserved.
