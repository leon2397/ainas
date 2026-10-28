@echo off
REM ── AINAS 本地开发启动脚本（Windows）────────────────────────────
REM
REM 不再在此硬编码 JWT 密钥。后端会按优先级自动获取：
REM   1) 环境变量 AI_NAS_JWT_SECRET
REM   2) data/.env 中的 AI_NAS_JWT_SECRET
REM   3) 自动生成随机密钥并写入 data/.env（仅首次）
REM
REM 需要固定密钥时（如要保持浏览器登录态），自行设置环境变量：
REM   set AI_NAS_JWT_SECRET=你的自定义密钥
REM
REM 生成的密钥写入 data/.env，该目录已在 .gitignore 中，不要提交。
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" main.py
) else if exist ".\venv\Scripts\python.exe" (
    ".\venv\Scripts\python.exe" main.py
) else (
    python main.py
)
