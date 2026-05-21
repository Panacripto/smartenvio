@echo off
chcp 65001 >nul
title Recompilar Instalador SmartEnvios
cd /d "%~dp0"

echo ========================================
echo  Recompilando instalador SmartEnvios
echo ========================================
echo.

REM 1. Compilar frontend
echo [1/4] Compilando frontend...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo ERROR al compilar frontend
    pause
    exit /b 1
)
cd ..
echo OK
echo.

REM 2. Limpiar carpeta app anterior
echo [2/4] Limpiando carpeta app anterior...
if exist "install\app" (
    rmdir /s /q "install\app"
)
mkdir "install\app"
echo OK
echo.

REM 3. Copiar archivos solo necesarios (sin basura)
echo [3/4] Copiando archivos de la app...

REM Archivos raiz
copy "%~dp0ejecutar.bat" "%~dp0install\app\ejecutar.bat" >nul
copy "%~dp0launcher.pyw" "%~dp0install\app\launcher.pyw" >nul
copy "%~dp0launcher.ico" "%~dp0install\app\launcher.ico" >nul
copy "%~dp0SELLO PROCESADO.png" "%~dp0install\app\SELLO PROCESADO.png" >nul

REM Backend (excluyendo temp_uploads, basura)
robocopy "%~dp0backend" "%~dp0install\app\backend" /E /XD "__pycache__" ".venv" "temp_uploads" /XF "*.pyc" "att_chk.txt" "att_chk2.txt" /R:0 /W:0 /NDL /NJH /NJS /NP >nul

REM Frontend (solo dist/, package.json, vite.config.ts)
robocopy "%~dp0frontend\dist" "%~dp0install\app\frontend\dist" /E /R:0 /W:0 /NDL /NJH /NJS /NP >nul
copy "%~dp0frontend\package.json" "%~dp0install\app\frontend\package.json" >nul
copy "%~dp0frontend\vite.config.ts" "%~dp0install\app\frontend\vite.config.ts" >nul

REM WhatsApp service (solo archivos necesarios, sin sesion ni cache)
robocopy "%~dp0whatsapp-service" "%~dp0install\app\whatsapp-service" /E /XD "__pycache__" ".wwebjs_cache" "node_modules" "session" "Cache" /XF "*.pyc" "qr_nuevo.png" "qr_temp.png" /R:0 /W:0 /NDL /NJH /NJS /NP >nul

REM Asegurar icono
if not exist "%~dp0install\app\launcher.ico" copy "%~dp0launcher.ico" "%~dp0install\app\launcher.ico" >nul
echo OK
echo.

REM 4. Compilar instalador
echo [4/4] Compilando instalador...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "install\setup.iss"
if %errorlevel% neq 0 (
    echo ERROR al compilar instalador
    pause
    exit /b 1
)
echo.
echo ========================================
echo  Instalador compilado exitosamente
echo ========================================
echo.
echo  Archivo: install\SmartEnvios_Installer_v1.0.exe
echo.
pause
