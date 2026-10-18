# AI-NAS Media Manager - 部署脚本
# Author: 梨子7
# Date: 2026-04-06

param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$UseDocker,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  AI-NAS Media Manager - 部署脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# 1. 前置检查
# ============================================================
Write-Host "[1/6] 检查环境..." -ForegroundColor Yellow

# 检查 Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  [OK] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python 未安装或未添加到 PATH" -ForegroundColor Red
    exit 1
}

# 检查 Node.js
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  [OK] Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Node.js 未安装，前端构建将跳过" -ForegroundColor Yellow
    $SkipFrontend = $true
}

# 检查 Docker (如果使用 Docker 部署)
if ($UseDocker) {
    try {
        $dockerVersion = docker --version 2>&1
        Write-Host "  [OK] Docker: $dockerVersion" -ForegroundColor Green
    } catch {
        Write-Host "  [ERROR] Docker 未安装" -ForegroundColor Red
        exit 1
    }
}

# ============================================================
# 2. 后端部署
# ============================================================
if (-not $SkipBackend) {
    Write-Host ""
    Write-Host "[2/6] 部署后端..." -ForegroundColor Yellow
    
    # 创建虚拟环境
    $venvPath = Join-Path $BackendDir "venv"
    if (-not (Test-Path $venvPath) -or $Force) {
        Write-Host "  创建虚拟环境..." -ForegroundColor Gray
        python -m venv $venvPath
    }
    
    # 激活虚拟环境
    & (Join-Path $venvPath "Scripts\Activate.ps1")
    
    # 升级 pip
    Write-Host "  升级 pip..." -ForegroundColor Gray
    python -m pip install --upgrade pip --quiet
    
    # 安装依赖
    Write-Host "  安装 Python 依赖..." -ForegroundColor Gray
    $requirementsFile = Join-Path $BackendDir "requirements.txt"
    if (Test-Path $requirementsFile) {
        python -m pip install -r $requirementsFile --quiet
    }
    
    Write-Host "  [OK] 后端部署完成" -ForegroundColor Green
}

# ============================================================
# 3. 前端构建
# ============================================================
if (-not $SkipFrontend) {
    Write-Host ""
    Write-Host "[3/6] 构建前端..." -ForegroundColor Yellow
    
    if (-not (Test-Path $FrontendDir)) {
        Write-Host "  [WARN] 前端目录不存在，跳过" -ForegroundColor Yellow
    } else {
        # 检查依赖
        $nodeModules = Join-Path $FrontendDir "node_modules"
        if (-not (Test-Path $nodeModules) -or $Force) {
            Write-Host "  安装 Node.js 依赖..." -ForegroundColor Gray
            Push-Location $FrontendDir
            npm install
            Pop-Location
        }
        
        # 构建前端
        Write-Host "  构建前端资源..." -ForegroundColor Gray
        # 前端资源会被 FastAPI 直接服务，不需要单独构建
        
        Write-Host "  [OK] 前端准备完成" -ForegroundColor Green
    }
}

# ============================================================
# 4. 环境配置
# ============================================================
Write-Host ""
Write-Host "[4/6] 配置环境..." -ForegroundColor Yellow

# 创建数据目录
$dataDir = Join-Path $ProjectRoot "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

# 创建日志目录
$logsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

# 创建上传目录
$uploadsDir = Join-Path $ProjectRoot "uploads"
if (-not (Test-Path $uploadsDir)) {
    New-Item -ItemType Directory -Path $uploadsDir | Out-Null
}

Write-Host "  [OK] 目录创建完成" -ForegroundColor Green

# ============================================================
# 5. Docker 部署 (可选)
# ============================================================
if ($UseDocker) {
    Write-Host ""
    Write-Host "[5/6] Docker 部署..." -ForegroundColor Yellow
    
    # 创建 .env 文件
    $envFile = Join-Path $ProjectRoot ".env"
    $envContent = @"
# AI-NAS Media Manager Environment
JWT_SECRET=ai-nas-secret-key-$(Get-Random -Maximum 999999)
BACKEND_PORT=8000
NAS_PATH=./nas
"@
    Set-Content -Path $envFile -Value $envContent -Encoding UTF8
    
    Write-Host "  启动 Docker 服务..." -ForegroundColor Gray
    docker compose up -d
    
    Write-Host "  [OK] Docker 服务已启动" -ForegroundColor Green
}

# ============================================================
# 6. 启动服务
# ============================================================
if (-not $UseDocker) {
    Write-Host ""
    Write-Host "[6/6] 启动服务..." -ForegroundColor Yellow
    
    # 激活虚拟环境
    $venvActivate = Join-Path $BackendDir "venv\Scripts\Activate.ps1"
    & $venvActivate
    
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "  启动 AI-NAS Media Manager..." -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  前端地址: http://localhost:8000" -ForegroundColor White
    Write-Host "  API 文档:  http://localhost:8000/docs" -ForegroundColor White
    Write-Host ""
    
    # 启动后端
    Set-Location $BackendDir
    python main.py
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  部署完成！" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
