[Setup]
AppName=Video Downloader
AppVersion=1.0
AppPublisher=Video Downloader
DefaultDirName={autopf}\VideoDownloader
DefaultGroupName=Video Downloader
AllowNoIcons=yes
OutputDir=C:\Users\kanwa\Desktop\tkdownload\tiktok-downloader\installer_output
OutputBaseFilename=VideoDownloaderSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=C:\Users\kanwa\Desktop\tkdownload\tiktok-downloader\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: desktopicon; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Files]
Source: "C:\Users\kanwa\Desktop\tkdownload\tiktok-downloader\dist\VideoDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Video Downloader";         Filename: "{app}\VideoDownloader.exe"
Name: "{group}\Uninstall Video Downloader"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Video Downloader"; Filename: "{app}\VideoDownloader.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VideoDownloader.exe"; Description: "Launch Video Downloader"; Flags: nowait postinstall skipifsilent
