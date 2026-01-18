@echo off
REM Ralph Codes 4 OpenCode - Windows Launcher
REM This script launches the Ralph GUI application

cd /d "%~dp0"

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Check if required packages are installed
python -c "import PIL" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing required packages...
    pip install -r requirements.txt
)

REM Launch the GUI detached from console (so command prompt closes immediately)
start "" pythonw ralph_gui.py
exit
