; SmartEnvios - InnoSetup Script
; Genera el instalador con: ISCC.exe "setup.iss"

#define MyAppName "SmartEnvios"
#define MyAppVersion "1.0"
#define MyAppPublisher "CriptoPana"
#define NodeVersion "22.14.0"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SmartEnvios
DefaultGroupName=SmartEnvios
UninstallDisplayIcon={app}\launcher.ico
OutputDir=.
OutputBaseFilename=SmartEnvios_Installer_v1.0
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
SetupIconFile=app\launcher.ico
WizardStyle=modern
WizardResizable=no
VersionInfoVersion=1.0.0
VersionInfoCompany=CriptoPana
VersionInfoDescription=Instalador de SmartEnvios - Plataforma de Mensajeria WhatsApp

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Types]
Name: "full"; Description: "Instalacion completa"
Name: "custom"; Description: "Instalacion personalizada"; Flags: iscustom

[Components]
Name: "app"; Description: "Aplicacion SmartEnvios"; Types: full custom; Flags: fixed
Name: "python"; Description: "Python 3.12.9 (32 bits)"; Types: full custom
Name: "nodejs"; Description: "Node.js 24.14.1"; Types: full custom
Name: "odbcdriver"; Description: "Controlador ODBC DBISAM 4"; Types: full custom
Name: "shortcuts"; Description: "Accesos directos"; Types: full custom

[Files]
; App files
Source: "app\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Components: app
; DBISAM ODBC Driver (32 bits)
Source: "drivers\win32\dbodbc.dll"; DestDir: "{app}\drivers"; Flags: ignoreversion; Components: odbcdriver
Source: "drivers\win64\dbodbc.dll"; DestDir: "{app}\drivers"; Flags: ignoreversion; Components: odbcdriver
; Python installer
Source: "installers\python-3.12.9.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall; Components: python
; Node.js installers (x64 para 64-bit, x86 para 32-bit)
Source: "installers\node-v{#NodeVersion}-x64.msi"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall; Components: nodejs; Check: IsWin64
Source: "installers\node-v{#NodeVersion}-x86.msi"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall; Components: nodejs; Check: not IsWin64

[Registry]
; === DBISAM ODBC Driver registration (32-bit) ===
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers"; ValueType: string; ValueName: "DBISAM 4 ODBC Driver"; ValueData: "Installed"; Flags: uninsdeletevalue; Components: odbcdriver; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "Driver"; ValueData: "{app}\drivers\dbodbc.dll"; Flags: uninsdeletekey; Components: odbcdriver; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "Setup"; ValueData: "{app}\drivers\dbodbc.dll"; Components: odbcdriver; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "APILevel"; ValueData: "1"; Components: odbcdriver; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "ConnectFunctions"; ValueData: "YYY"; Components: odbcdriver; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "DriverODBCVer"; ValueData: "03.00"; Components: odbcdriver; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "FileExtns"; ValueData: "*.dat,*.idx,*.blb"; Components: odbcdriver; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "FileUsage"; ValueData: "1"; Components: odbcdriver; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "SQLLevel"; ValueData: "0"; Components: odbcdriver; Check: not IsWin64
; 64-bit system - register in 32-bit WOW6432Node
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBCINST.INI\ODBC Drivers"; ValueType: string; ValueName: "DBISAM 4 ODBC Driver"; ValueData: "Installed"; Flags: uninsdeletevalue; Components: odbcdriver; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "Driver"; ValueData: "{app}\drivers\dbodbc.dll"; Flags: uninsdeletekey; Components: odbcdriver; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "Setup"; ValueData: "{app}\drivers\dbodbc.dll"; Components: odbcdriver; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "APILevel"; ValueData: "1"; Components: odbcdriver; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "ConnectFunctions"; ValueData: "YYY"; Components: odbcdriver; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "DriverODBCVer"; ValueData: "03.00"; Components: odbcdriver; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "FileExtns"; ValueData: "*.dat,*.idx,*.blb"; Components: odbcdriver; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "FileUsage"; ValueData: "1"; Components: odbcdriver; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBCINST.INI\DBISAM 4 ODBC Driver"; ValueType: string; ValueName: "SQLLevel"; ValueData: "0"; Components: odbcdriver; Check: IsWin64

; === DSN HAC_HO (System DSN, 32-bit) ===
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBC.INI\ODBC Data Sources"; ValueType: string; ValueName: "HAC_HO"; ValueData: "DBISAM 4 ODBC Driver"; Flags: uninsdeletevalue; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBC.INI\HAC_HO"; ValueType: string; ValueName: "Driver"; ValueData: "{app}\drivers\dbodbc.dll"; Flags: uninsdeletekey; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBC.INI\HAC_HO"; ValueType: string; ValueName: "CatalogName"; ValueData: "{code:GetDBDir}"; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBC.INI\HAC_HO"; ValueType: string; ValueName: "ConnectionType"; ValueData: "Local"; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBC.INI\HAC_HO"; ValueType: dword; ValueName: "LockWaitTime"; ValueData: "100"; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBC.INI\HAC_HO"; ValueType: dword; ValueName: "LockRetryCount"; ValueData: "15"; Check: not IsWin64
Root: HKLM; Subkey: "SOFTWARE\ODBC\ODBC.INI\HAC_HO"; ValueType: string; ValueName: "ReadOnly"; ValueData: "False"; Check: not IsWin64
; 64-bit: system DSN in WOW6432Node
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBC.INI\ODBC Data Sources"; ValueType: string; ValueName: "HAC_HO"; ValueData: "DBISAM 4 ODBC Driver"; Flags: uninsdeletevalue; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBC.INI\HAC_HO"; ValueType: string; ValueName: "Driver"; ValueData: "{app}\drivers\dbodbc.dll"; Flags: uninsdeletekey; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBC.INI\HAC_HO"; ValueType: string; ValueName: "CatalogName"; ValueData: "{code:GetDBDir}"; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBC.INI\HAC_HO"; ValueType: string; ValueName: "ConnectionType"; ValueData: "Local"; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBC.INI\HAC_HO"; ValueType: dword; ValueName: "LockWaitTime"; ValueData: "100"; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBC.INI\HAC_HO"; ValueType: dword; ValueName: "LockRetryCount"; ValueData: "15"; Check: IsWin64
Root: HKLM; Subkey: "SOFTWARE\WOW6432Node\ODBC\ODBC.INI\HAC_HO"; ValueType: string; ValueName: "ReadOnly"; ValueData: "False"; Check: IsWin64

[Run]
; 1. Install Python 3.12.9 (32-bit) with pip
Filename: "{tmp}\python-3.12.9.exe"; Parameters: "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1"; StatusMsg: "Instalando Python 3.12.9..."; Components: python; Flags: skipifdoesntexist
; 1b. Ensure pip is installed (safety net)
Filename: "{cmd}"; Parameters: "/c ""{code:GetPythonPath}"" -m ensurepip --upgrade >nul 2>nul"; StatusMsg: "Verificando pip..."; Flags: runhidden
; 2. Install Node.js
Filename: "msiexec"; Parameters: "/i ""{tmp}\node-v{#NodeVersion}-x64.msi"" /quiet /norestart"; StatusMsg: "Instalando Node.js..."; Components: nodejs; Check: IsWin64
Filename: "msiexec"; Parameters: "/i ""{tmp}\node-v{#NodeVersion}-x86.msi"" /quiet /norestart"; StatusMsg: "Instalando Node.js..."; Components: nodejs; Check: not IsWin64
; 3. Install Python dependencies
Filename: "{cmd}"; Parameters: "/c ""{code:GetPythonPath}"" -m pip install -r ""{app}\backend\requirements.txt"""; StatusMsg: "Instalando dependencias de Python..."; Flags: runhidden
; 4. Create ODBC config file
Filename: "{cmd}"; Parameters: "/c echo {{""dsn"": ""HAC_HO""}} > ""{app}\backend\odbc_config.json"""; Flags: runhidden

[Icons]
Name: "{commondesktop}\SmartEnvios"; Filename: "{code:GetPythonPath}"; Parameters: """{app}\launcher.pyw"""; IconFilename: "{app}\launcher.ico"; WorkingDir: "{app}"; Comment: "SmartEnvios - Plataforma de Mensajeria WhatsApp"; Components: shortcuts
Name: "{group}\SmartEnvios"; Filename: "{code:GetPythonPath}"; Parameters: """{app}\launcher.pyw"""; IconFilename: "{app}\launcher.ico"; WorkingDir: "{app}"; Components: shortcuts
Name: "{group}\Desinstalar SmartEnvios"; Filename: "{uninstallexe}"; Components: shortcuts

[Code]
var
  DBPage: TWizardPage;
  DBEdit: TEdit;
  DBBrowseBtn: TButton;
  DBLabel: TLabel;
  DBFolder: string;

{ Devuelve la carpeta DBISAM seleccionada }
function GetDBDir(Param: string): string;
begin
  Result := DBFolder;
end;

{ Devuelve la ruta completa a npm.cmd segun la arquitectura }
function GetNpmPath(Param: string): string;
begin
  if IsWin64 then
    Result := ExpandConstant('{pf}\nodejs\npm.cmd')
  else
    Result := ExpandConstant('{pf}\nodejs\npm.cmd');
end;

{ Busca python.exe en el sistema }
function GetPythonPath(Param: string): string;
var
  PythonExe: string;
  RegPath: string;
begin
  Result := '';

  { 1. Buscar en registro HKLM (all-users) - mas confiable }
  RegPath := 'SOFTWARE\Python\PythonCore\3.12\InstallPath';
  if IsWin64 then
    RegPath := 'SOFTWARE\WOW6432Node\Python\PythonCore\3.12\InstallPath';
  if RegQueryStringValue(HKLM, RegPath, '', PythonExe) then
  begin
    PythonExe := PythonExe + 'python.exe';
    if FileExists(PythonExe) then
    begin
      Result := PythonExe;
      Exit;
    end;
  end;

  { 2. Buscar en registro HKCU (per-user) }
  RegPath := 'SOFTWARE\Python\PythonCore\3.12\InstallPath';
  if RegQueryStringValue(HKCU, RegPath, '', PythonExe) then
  begin
    PythonExe := PythonExe + 'python.exe';
    if FileExists(PythonExe) then
    begin
      Result := PythonExe;
      Exit;
    end;
  end;

  { 3. Buscar en rutas comunes (ProgramFiles) }
  PythonExe := ExpandConstant('{pf}') + '\Python312\python.exe';
  if FileExists(PythonExe) then
  begin
    Result := PythonExe;
    Exit;
  end;

  PythonExe := ExpandConstant('{pf}') + '\Python312-32\python.exe';
  if FileExists(PythonExe) then
  begin
    Result := PythonExe;
    Exit;
  end;

  if IsWin64 then
    PythonExe := 'C:\Program Files (x86)\Python312-32\python.exe'
  else
    PythonExe := 'C:\Program Files\Python312-32\python.exe';
  if FileExists(PythonExe) then
  begin
    Result := PythonExe;
    Exit;
  end;

  PythonExe := 'C:\Python312-32\python.exe';
  if FileExists(PythonExe) then
  begin
    Result := PythonExe;
    Exit;
  end;

  { 4. Buscar en AppData (per-user) }
  PythonExe := ExpandConstant('{localappdata}') + '\Programs\Python\Python312-32\python.exe';
  if FileExists(PythonExe) then
  begin
    Result := PythonExe;
    Exit;
  end;

  PythonExe := ExpandConstant('{userappdata}') + '\Programs\Python\Python312-32\python.exe';
  if FileExists(PythonExe) then
  begin
    Result := PythonExe;
    Exit;
  end;

  { 5. Si no se encuentra, usar python.exe del PATH como fallback }
  Result := 'python.exe';
end;

{ Evento: al hacer clic en Browse }
procedure BrowseDBDir(Sender: TObject);
var
  Folder: string;
begin
  if BrowseForFolder('Selecciona la carpeta donde estan los archivos DBISAM (.dat, .idx):', Folder, False) then
  begin
    DBFolder := Folder;
    DBEdit.Text := Folder;
  end;
end;

{ Crea la pagina personalizada para la carpeta DBISAM }
procedure CreateDBPage();
begin
  DBPage := CreateCustomPage(wpSelectDir,
    'Carpeta de datos DBISAM',
    'Indica donde estan tus archivos de base de datos DBISAM');

  DBLabel := TLabel.Create(DBPage);
  DBLabel.Parent := DBPage.Surface;
  DBLabel.Caption :=
    'Selecciona la carpeta que contiene los archivos .dat de tu sistema' + #13#10 +
    '(ej: C:\HAC\Datos\ o D:\a2apps\HAC_HO\Empre001\Data\)';
  DBLabel.Left := 0;
  DBLabel.Top := 0;
  DBLabel.Width := DBPage.SurfaceWidth;
  DBLabel.Height := 30;

  DBEdit := TEdit.Create(DBPage);
  DBEdit.Parent := DBPage.Surface;
  DBEdit.Left := 0;
  DBEdit.Top := 40;
  DBEdit.Width := DBPage.SurfaceWidth - 70;
  DBEdit.Text := '';
  DBEdit.ReadOnly := True;

  DBBrowseBtn := TButton.Create(DBPage);
  DBBrowseBtn.Parent := DBPage.Surface;
  DBBrowseBtn.Left := DBPage.SurfaceWidth - 65;
  DBBrowseBtn.Top := 38;
  DBBrowseBtn.Width := 65;
  DBBrowseBtn.Height := 25;
  DBBrowseBtn.Caption := 'Examinar...';
  DBBrowseBtn.OnClick := @BrowseDBDir;
end;

{ Inicializacion }
procedure InitializeWizard();
begin
  DBFolder := '';
  CreateDBPage();
end;

{ Validacion: la carpeta debe seleccionarse }
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = DBPage.ID then
  begin
    if DBFolder = '' then
    begin
      MsgBox('Debes seleccionar la carpeta donde estan tus datos DBISAM.', mbError, MB_OK);
      Result := False;
    end
    else if not DirExists(DBFolder) then
    begin
      MsgBox('La carpeta seleccionada no existe. Verifica la ruta.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

{ Limpiar drivers al desinstalar }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if DirExists(ExpandConstant('{app}\drivers')) then
      DelTree(ExpandConstant('{app}\drivers'), True, True, True);
  end;
end;
