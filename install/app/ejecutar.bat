@echo off
cd /d "%~dp0"
echo Buscando Python...

set PYTHON_EXE=

if exist "%LocalAppData%\Programs\Python\Python312-32\python.exe" (
    "%LocalAppData%\Programs\Python\Python312-32\python.exe" -c "import json" >nul 2>&1
    if not errorlevel 1 set PYTHON_EXE=%LocalAppData%\Programs\Python\Python312-32\python.exe
)

if not defined PYTHON_EXE if exist "%AppData%\Programs\Python\Python312-32\python.exe" (
    "%AppData%\Programs\Python\Python312-32\python.exe" -c "import json" >nul 2>&1
    if not errorlevel 1 set PYTHON_EXE=%AppData%\Programs\Python\Python312-32\python.exe
)

if not defined PYTHON_EXE if exist "C:\Python312-32\python.exe" (
    "C:\Python312-32\python.exe" -c "import json" >nul 2>&1
    if not errorlevel 1 set PYTHON_EXE=C:\Python312-32\python.exe
)

if not defined PYTHON_EXE (
    where python >nul 2>&1
    if not errorlevel 1 set PYTHON_EXE=python
)

if not defined PYTHON_EXE (
    echo ERROR: No se encuentra Python 3.12 funcional.
    pause
    exit /b 1
)

echo Usando: %PYTHON_EXE%
echo.
echo Iniciando SmartEnvios...
"%PYTHON_EXE%" "%~dp0launcher.pyw"
pause
