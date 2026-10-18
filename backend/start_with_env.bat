@echo off
set AI_NAS_JWT_SECRET=ai-nas-dev-secret-key-2026
cd /d "%~dp0"
.\venv\Scripts\python.exe main.py
