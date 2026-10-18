@echo off
chcp 65001 >nul
REM ==========================================
REM   AI-NAS 测试运行脚本
REM ==========================================

echo.
echo ==========================================
echo   AI-NAS Media Manager - 测试
echo ==========================================
echo.

cd /d %~dp0

REM 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] 虚拟环境不存在
    echo 请先运行: python -m venv venv
    pause
    exit /b 1
)

REM 激活虚拟环境并运行测试
echo [INFO] 运行测试...
echo.

venv\Scripts\python.exe -m pytest tests\ -v --tb=short

echo.
echo ==========================================
echo   测试完成
echo ==========================================
pause
