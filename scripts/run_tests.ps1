# AI-NAS Media Manager - 测试运行脚本
# 一键运行所有测试

param(
    [Parameter()]
    [ValidateSet("all", "unit", "integration", "e2e", "performance")]
    [string]$TestType = "all",
    
    [switch]$Coverage,
    [switch]$Verbose,
    [switch]$FailFast
)

$ErrorActionPreference = "Stop"
$VerbosePreference = if ($Verbose) { "Continue" } else { "SilentlyContinue" }

# 颜色定义
$colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
}

function Write-ColorLine {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $colors[$Color]
}

function Test-Command {
    param([string]$Command)
    return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

# 标题
Write-ColorLine "`n============================================" $colors.Info
Write-ColorLine "  AI-NAS Media Manager - 测试套件" $colors.Info
Write-ColorLine "============================================" $colors.Info
Write-ColorLine ""

# 检查环境
Write-ColorLine "📋 检查测试环境..." $colors.Info

$checks = @(
    @{ Name = "Python"; Command = "python --version" },
    @{ Name = "Node.js"; Command = "node --version" },
    @{ Name = "Backend"; Path = "backend/main.py" },
    @{ Name = "Tests"; Path = "tests" }
)

$allPassed = $true
foreach ($check in $checks) {
    if ($check.Command) {
        $result = Invoke-Expression $check.Command 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorLine "  ✅ $($check.Name): $result" $colors.Success
        } else {
            Write-ColorLine "  ❌ $($check.Name): 未安装" $colors.Error
            $allPassed = $false
        }
    } else {
        if (Test-Path $check.Path) {
            Write-ColorLine "  ✅ $($check.Name): 已找到" $colors.Success
        } else {
            Write-ColorLine "  ❌ $($check.Name): 未找到 ($($check.Path))" $colors.Error
            $allPassed = $false
        }
    }
}

if (-not $allPassed) {
    Write-ColorLine "`n❌ 环境检查失败，请安装缺失的依赖" $colors.Error
    exit 1
}

# 安装测试依赖
Write-ColorLine "`n📦 安装测试依赖..." $colors.Info

cd backend

$testDeps = @(
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "httpx",
    "websockets"
)

foreach ($dep in $testDeps) {
    pip show $dep 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-ColorLine "  安装 $dep..." $colors.Warning
        pip install $dep -q
    }
}

cd ..

# 运行单元测试
if ($TestType -in @("all", "unit")) {
    Write-ColorLine "`n🧪 运行单元测试..." $colors.Info
    
    $pytestArgs = @(
        "-v",
        "tests/unit"
    )
    
    if ($Coverage) {
        $pytestArgs += @("--cov=backend", "--cov-report=html", "--cov-report=term")
    }
    
    if ($FailFast) {
        $pytestArgs += "-x"
    }
    
    cd backend
    $output = & python -m pytest $pytestArgs 2>&1
    $exitCode = $LASTEXITCODE
    cd ..
    
    if ($exitCode -eq 0) {
        Write-ColorLine "  ✅ 单元测试通过" $colors.Success
    } else {
        Write-ColorLine "  ❌ 单元测试失败" $colors.Error
        Write-ColorLine $output $colors.Error
        if ($FailFast) { exit 1 }
    }
}

# 启动后端服务进行集成测试
if ($TestType -in @("all", "integration", "e2e")) {
    Write-ColorLine "`n🚀 启动后端服务..." $colors.Info
    
    # 检查服务是否已在运行
    $serviceRunning = $false
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 2
        if ($response.status -eq "healthy") {
            $serviceRunning = $true
            Write-ColorLine "  ✅ 服务已在运行" $colors.Success
        }
    } catch {
        $serviceRunning = $false
    }
    
    $serviceProcess = $null
    if (-not $serviceRunning) {
        # 启动服务
        $serviceProcess = Start-Process -FilePath "python" -ArgumentList "backend/main.py" -PassThru -WindowStyle Hidden
        
        # 等待服务启动
        Write-ColorLine "  等待服务启动..." $colors.Warning
        $maxRetries = 30
        $retry = 0
        $started = $false
        
        while ($retry -lt $maxRetries -and -not $started) {
            Start-Sleep -Seconds 1
            try {
                $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 2
                if ($response.status -eq "healthy") {
                    $started = $true
                    Write-ColorLine "  ✅ 服务启动成功" $colors.Success
                }
            } catch {
                $retry++
            }
        }
        
        if (-not $started) {
            Write-ColorLine "  ❌ 服务启动失败" $colors.Error
            exit 1
        }
    }
}

# 运行集成测试
if ($TestType -in @("all", "integration")) {
    Write-ColorLine "`n🔗 运行集成测试..." $colors.Info
    
    cd backend
    $output = & python -m pytest ../tests/integration -v --timeout=60 2>&1
    $exitCode = $LASTEXITCODE
    cd ..
    
    if ($exitCode -eq 0) {
        Write-ColorLine "  ✅ 集成测试通过" $colors.Success
    } else {
        Write-ColorLine "  ❌ 集成测试失败" $colors.Error
        if ($FailFast) { 
            if ($serviceProcess) { Stop-Process -Id $serviceProcess.Id -Force -ErrorAction SilentlyContinue }
            exit 1 
        }
    }
}

# 运行E2E测试
if ($TestType -in @("all", "e2e")) {
    Write-ColorLine "`n🎭 运行E2E测试..." $colors.Info
    
    # 检查Playwright
    cd tests/e2e
    
    if (-not (Test-Path "node_modules")) {
        Write-ColorLine "  安装E2E依赖..." $colors.Warning
        npm install
    }
    
    if (-not (Test-Path (Join-Path $env:USERPROFILE ".cache\ms-playwright"))) {
        Write-ColorLine "  安装Playwright浏览器..." $colors.Warning
        npx playwright install chromium
    }
    
    $output = & npx playwright test --project=chromium 2>&1
    $exitCode = $LASTEXITCODE
    cd ..\..
    
    if ($exitCode -eq 0) {
        Write-ColorLine "  ✅ E2E测试通过" $colors.Success
    } else {
        Write-ColorLine "  ❌ E2E测试失败" $colors.Error
        Write-ColorLine "  查看报告: tests/e2e/playwright-report/" $colors.Warning
        if ($FailFast) { 
            if ($serviceProcess) { Stop-Process -Id $serviceProcess.Id -Force -ErrorAction SilentlyContinue }
            exit 1 
        }
    }
}

# 停止服务
if ($serviceProcess) {
    Write-ColorLine "`n🛑 停止后端服务..." $colors.Info
    Stop-Process -Id $serviceProcess.Id -Force -ErrorAction SilentlyContinue
    Write-ColorLine "  ✅ 服务已停止" $colors.Success
}

# 运行性能测试
if ($TestType -eq "performance") {
    Write-ColorLine "`n⚡ 运行性能测试..." $colors.Info
    Write-ColorLine "  启动 Locust..." $colors.Warning
    Write-ColorLine "  访问 http://localhost:8089 查看测试界面" $colors.Info
    
    cd tests/performance
    & locust -f locustfile.py --host=http://localhost:8000
    cd ..\..
}

# 总结
Write-ColorLine "`n============================================" $colors.Info
Write-ColorLine "  测试完成!" $colors.Success
Write-ColorLine "============================================" $colors.Info

if ($Coverage -and $TestType -in @("all", "unit")) {
    Write-ColorLine "`n📊 覆盖率报告: backend/htmlcov/index.html" $colors.Info
}
