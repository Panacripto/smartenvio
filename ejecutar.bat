@echo off
cd /d "%~dp0"

set PYTHON_EXE=

if exist "%LocalAppData%\Programs\Python\Python312-32\pythonw.exe" (
    "%LocalAppData%\Programs\Python\Python312-32\pythonw.exe" -c "import json" >nul 2>&1
    if not errorlevel 1 set PYTHON_EXE=%LocalAppData%\Programs\Python\Python312-32\pythonw.exe
)

if not defined PYTHON_EXE if exist "%AppData%\Programs\Python\Python312-32\pythonw.exe" (
    "%AppData%\Programs\Python\Python312-32\pythonw.exe" -c "import json" >nul 2>&1
    if not errorlevel 1 set PYTHON_EXE=%AppData%\Programs\Python\Python312-32\pythonw.exe
)

if not defined PYTHON_EXE if exist "C:\Python312-32\pythonw.exe" (
    "C:\Python312-32\pythonw.exe" -c "import json" >nul 2>&1
    if not errorlevel 1 set PYTHON_EXE=C:\Python312-32\pythonw.exe
)

if not defined PYTHON_EXE (
    where pythonw >nul 2>&1
    if not errorlevel 1 set PYTHON_EXE=pythonw
)

if not defined PYTHON_EXE (
    cls
    exit /b 1
)

start "" /B "%PYTHON_EXE%" "%~dp0launcher.pyw" >nul 2>&1
exit
