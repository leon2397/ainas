@echo off
cd /d C:\Users\leon23973\.qclaw\workspace\ai-nas-media-manager\backend
call venv\Scripts\activate.bat
python -m uvicorn main:app --host 0.0.0.0 --port 8000