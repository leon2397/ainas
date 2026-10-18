@echo off
cd /d "%~dp0"

echo [AI-NAS] Starting...

REM Check if venv exists
if not exist venv (
    echo [AI-NAS] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv. Make sure Python is installed.
        pause
        exit /b 1
    )
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies
echo [AI-NAS] Installing dependencies...
pip install -r requirements.txt -q

REM Start server
echo [AI-NAS] Starting server on http://localhost:8000
python main.py

pause
