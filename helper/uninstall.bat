@echo off
setlocal
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" install_host.py --uninstall
) else (
    py -3 install_host.py --uninstall
)
if exist "venv" rmdir /s /q "venv"
echo Helper uninstalled.
endlocal
