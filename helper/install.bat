@echo off
setlocal
cd /d "%~dp0"

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo Python 3.10 or later is required.
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    py -3 -m venv venv
    if errorlevel 1 exit /b 1
)
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

"venv\Scripts\python.exe" install_host.py
if errorlevel 1 exit /b 1

echo Helper installed for Firefox.
echo Open the Quick Web Clip options page in Firefox: it should say "Helper connected".
endlocal
