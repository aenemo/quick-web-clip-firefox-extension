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

echo Helper installed.
echo Next step: load the extension in Firefox (about:debugging, This Firefox, Load Temporary Add-on).
echo For Chrome or Edge, run "py -3 tools\build_chromium.py" from the repository folder,
echo then load dist\chrome or dist\edge with Load unpacked (Developer mode on).
endlocal
