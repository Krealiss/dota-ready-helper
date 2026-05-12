; Inno Setup Script для Dota Ready Helper
; Версія: 2.1

#define MyAppName "Dota Ready Helper"
#define MyAppVersion "2.1"
#define MyAppPublisher "DotaHelper"
#define MyAppURL "https://dotahelper.app"
#define MyAppExeName "DotaReadyHelper.exe"

[Setup]
AppId={{A7B8C9D0-E1F2-3456-7890-ABCDEF123456}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=installer
OutputBaseFilename=DotaReadyHelper_Setup_v{#MyAppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "autostart"; Description: "Запускати при старті Windows"; GroupDescription: "Додатково:"; Flags: unchecked

[Files]
; Головний виконуваний файл (onefile build)
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Assets
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

; Конфігурація (шаблон)
Source: ".env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion

; Документація
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "QUICKSTART.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Документація"; Filename: "{app}\README.md"
Name: "{group}\Швидкий старт"; Filename: "{app}\QUICKSTART.md"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; Автозапуск
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Запропонувати налаштувати .env після встановлення
Filename: "notepad.exe"; Parameters: """{app}\.env.example"""; Description: "Налаштувати конфігурацію (.env)"; Flags: postinstall shellexec skipifsilent nowait

; Запустити програму
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: postinstall skipifsilent nowait

[Code]
var
  ConfigPage: TInputQueryWizardPage;
  TelegramTokenEdit: TEdit;
  TelegramChatIdEdit: TEdit;

procedure InitializeWizard;
begin
  // Створити сторінку для введення Telegram токенів
  ConfigPage := CreateInputQueryPage(wpSelectTasks,
    'Налаштування Telegram',
    'Введіть дані вашого Telegram бота',
    'Для роботи програми потрібен Telegram бот. Якщо у вас ще немає бота, пропустіть цей крок і налаштуйте пізніше.');

  ConfigPage.Add('Telegram Bot Token:', False);
  ConfigPage.Add('Telegram Chat ID:', False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvFile: string;
  EnvContent: TStringList;
begin
  if CurStep = ssPostInstall then
  begin
    // Створити .env файл з введеними даними
    if (ConfigPage.Values[0] <> '') and (ConfigPage.Values[1] <> '') then
    begin
      EnvFile := ExpandConstant('{app}\.env');
      EnvContent := TStringList.Create;
      try
        EnvContent.Add('# Telegram Bot Configuration');
        EnvContent.Add('TELEGRAM_BOT_TOKEN=' + ConfigPage.Values[0]);
        EnvContent.Add('TELEGRAM_CHAT_ID=' + ConfigPage.Values[1]);
        EnvContent.Add('');
        EnvContent.Add('# Image Recognition Settings');
        EnvContent.Add('CONFIDENCE_ACCEPT=0.80');
        EnvContent.Add('CONFIDENCE_SEARCHING=0.70');
        EnvContent.Add('CONFIDENCE_SEARCH_BTN=0.70');
        EnvContent.Add('CONFIDENCE_STOP_BTN=0.75');
        EnvContent.Add('');
        EnvContent.Add('# Timing Settings (in seconds)');
        EnvContent.Add('SCAN_INTERVAL=0.30');
        EnvContent.Add('CLICK_COOLDOWN=1.00');
        EnvContent.Add('MESSAGE_COOLDOWN=5.00');

        EnvContent.SaveToFile(EnvFile);
      finally
        EnvContent.Free;
      end;
    end;
  end;
end;

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\stats"
Type: files; Name: "{app}\.env"
