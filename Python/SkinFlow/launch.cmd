@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Create the project virtual environment and install dependencies first. See README.md.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m skinflow
