@echo off
REM AI-NAS Media Manager - Windows Quick Start Script
REM Run this script to quickly start the AI-NAS Media Manager

echo ==========================================
echo   AI-NAS Media Manager - Quick Start
echo ==========================================
echo.

REM Get script directory
set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%backend

REM Check if virtual environment exists
if not exist "%BACKEND_DIR%\venv" (
    echo [1/4] Creating virtual environment...
    cd /d "%BACKEND_DIR%"
    python -m venv venv
) else (
    echo [OK] Virtual environment exists
)

REM Activate virtual environment
echo [2/4] Activating virtual environment...
call "%BACKEND_DIR%\venv\Scripts\activate.bat"

REM Upgrade pip
echo [3/4] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo [4/4] Installing dependencies...
pip install -r requirements.txt

REM Start the server
echo.
echo ==========================================
echo   Starting AI-NAS Media Manager...
echo ==========================================
echo.
echo   Frontend: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.

cd /d "%BACKEND_DIR%"
python main.py

pause
