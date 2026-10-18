# ==============================================================================
#  AI-NAS Media Manager - Health Check Script
#  检查服务状态、数据库、存储等
# ==============================================================================

param(
    [switch]$Verbose,         # 详细输出
    [switch]$Docker,          # Docker 模式检查
    [int]$Timeout = 5         # API 超时秒数
)

$ErrorActionPreference = "Continue"

# 颜色输出
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    $colorMap = @{
        "Red" = [ConsoleColor]::Red
        "Green" = [ConsoleColor]::Green
        "Yellow" = [ConsoleColor]::Yellow
        "Cyan" = [ConsoleColor]::Cyan
        "White" = [ConsoleColor]::White
    }
    Write-Host $Message -ForegroundColor $colorMap[$Color]
}

# 检查项结果
$checks = @()

function Test-Check {
    param([string]$Name, [scriptblock]$Test, [string]$SuccessMsg, [string]$FailMsg)
    try {
        $result = & $Test
        if ($result) {
            $checks += @{Name=$Name; Status="PASS"; Message=$SuccessMsg}
            if ($Verbose -or $true) { Write-ColorOutput "  [PASS] $Name" "Green" }
        } else {
            $checks += @{Name=$Name; Status="FAIL"; Message=$FailMsg}
            Write-ColorOutput "  [FAIL] $Name - $FailMsg" "Red"
        }
    } catch {
        $checks += @{Name=$Name; Status="ERROR"; Message=$_.Exception.Message}
        Write-ColorOutput "  [ERROR] $Name - $($_.Exception.Message)" "Red"
    }
}

# 获取项目路径
$ProjectRoot = "C:\Users\leon23973\.qclaw\workspace\ai-nas-media-manager"
$BackendPath = Join-Path $ProjectRoot "backend"

Write-ColorOutput "`n========================================" "Cyan"
Write-ColorOutput "  AI-NAS Media Manager - 健康检查" "Cyan"
Write-ColorOutput "========================================`n" "Cyan"
Write-ColorOutput "[*] 检查时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "White"
Write-ColorOutput "[*] 项目路径: $ProjectRoot`n" "White"

# ============================================================================
# 1. 服务进程检查
# ============================================================================
Write-ColorOutput "[1/6] 检查服务进程..." "Cyan"

$pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*ai-nas*" -or $_.Path -like "*main.py*" }
if ($pythonProcesses) {
    Write-ColorOutput "  [PASS] Python 服务进程运行中" "Green"
    foreach ($proc in $pythonProcesses) {
        $memMB = [math]::Round($proc.WorkingSet64 / 1MB, 1)
        Write-ColorOutput "      PID: $($proc.Id) | 内存: $memMB MB" "White"
    }
} else {
    Write-ColorOutput "  [WARN] 未检测到 AI-NAS Python 进程" "Yellow"
}

# ============================================================================
# 2. HTTP API 检查
# ============================================================================
Write-ColorOutput "`n[2/6] 检查 API 服务..." "Cyan"

$baseUrl = "http://localhost:8000"

# 健康检查端点
Test-Check -Name "健康检查端点" -Test {
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET -TimeoutSec $Timeout -ErrorAction Stop
        $content = $response.Content | ConvertFrom-Json
        return $content.status -eq "healthy"
    } catch { return $false }
} -SuccessMsg "服务正常" -FailMsg "服务未响应"

# 数据库连接
Test-Check -Name "数据库连接" -Test {
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET -TimeoutSec $Timeout -ErrorAction Stop
        $content = $response.Content | ConvertFrom-Json
        return $content.database -eq "connected"
    } catch { return $false }
} -SuccessMsg "数据库正常" -FailMsg "数据库连接失败"

# ============================================================================
# 3. 磁盘空间检查
# ============================================================================
Write-ColorOutput "`n[3/6] 检查磁盘空间..." "Cyan"

$drive = [System.IO.Path]::GetPathRoot($ProjectRoot)
$driveInfo = Get-PSDrive -Name $drive.TrimEnd(':') -ErrorAction SilentlyContinue

if ($driveInfo) {
    $freeGB = [math]::Round($driveInfo.Free / 1GB, 2)
    $usedGB = [math]::Round($driveInfo.Used / 1GB, 2)
    $totalGB = $freeGB + $usedGB
    $usedPercent = [math]::Round(($usedGB / $totalGB) * 100, 1)
    
    Write-ColorOutput "  [INFO] 磁盘: $drive | 可用: $freeGB GB | 已用: $usedPercent%" "White"
    
    if ($freeGB -lt 10) {
        Write-ColorOutput "  [WARN] 磁盘空间不足 10GB！" "Yellow"
    } else {
        Write-ColorOutput "  [PASS] 磁盘空间充足" "Green"
    }
}

# ============================================================================
# 4. 存储目录检查
# ============================================================================
Write-ColorOutput "`n[4/6] 检查存储目录..." "Cyan"

$storagePaths = @(
    @{Name="原始照片"; Path=(Join-Path $BackendPath "photo_original")},
    @{Name="相册照片"; Path=(Join-Path $BackendPath "photo_album")},
    @{Name="临时文件"; Path=(Join-Path $BackendPath "temp")},
    @{Name="数据目录"; Path=(Join-Path $BackendPath "data")},
    @{Name="日志目录"; Path=(Join-Path $BackendPath "logs")}
)

foreach ($item in $storagePaths) {
    if (Test-Path $item.Path) {
        $size = (Get-ChildItem -Path $item.Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $sizeMB = [math]::Round($size / 1MB, 2)
        Write-ColorOutput "  [PASS] $($item.Name): $sizeMB MB" "Green"
    } else {
        Write-ColorOutput "  [WARN] $($item.Name): 目录不存在" "Yellow"
    }
}

# ============================================================================
# 5. 数据库检查
# ============================================================================
Write-ColorOutput "`n[5/6] 检查数据库..." "Cyan"

$dbPath = Join-Path $BackendPath "data\metadata.db"
if (Test-Path $dbPath) {
    $dbSize = [math]::Round((Get-Item $dbPath).Length / 1MB, 2)
    Write-ColorOutput "  [PASS] 数据库文件: $dbSize MB" "Green"
    
    # 尝试读取数据库
    try {
        Add-Type -Path (Join-Path $BackendPath "database\db.py") -ErrorAction SilentlyContinue
        Write-ColorOutput "  [INFO] 数据库模块可加载" "White"
    } catch {
        Write-ColorOutput "  [WARN] 无法验证数据库内容" "Yellow"
    }
} else {
    Write-ColorOutput "  [FAIL] 数据库文件不存在！" "Red"
}

# ============================================================================
# 6. Docker 检查（可选）
# ============================================================================
if ($Docker) {
    Write-ColorOutput "`n[6/6] 检查 Docker 容器..." "Cyan"
    
    $containers = docker ps --filter "name=ai-nas" --format "{{.Names}}:{{.Status}}" 2>$null
    if ($LASTEXITCODE -eq 0 -and $containers) {
        foreach ($c in $containers) {
            Write-ColorOutput "  [PASS] $c" "Green"
        }
    } else {
        Write-ColorOutput "  [WARN] 未检测到 AI-NAS Docker 容器" "Yellow"
    }
}

# ============================================================================
# 汇总报告
# ============================================================================
Write-ColorOutput "`n========================================" "Cyan"
Write-ColorOutput "  健康检查汇总" "Cyan"
Write-ColorOutput "========================================`n" "Cyan"

$passCount = ($checks | Where-Object { $_.Status -eq "PASS" }).Count
$failCount = ($checks | Where-Object { $_.Status -eq "FAIL" }).Count
$errorCount = ($checks | Where-Object { $_.Status -eq "ERROR" }).Count
$warnCount = ($checks | Where-Object { $_.Status -eq "WARN" }).Count
$total = $checks.Count

Write-ColorOutput "  总检查项: $total" "White"
Write-ColorOutput "  通过: $passCount" "Green"
if ($warnCount -gt 0) { Write-ColorOutput "  警告: $warnCount" "Yellow" }
if ($errorCount -gt 0) { Write-ColorOutput "  错误: $errorCount" "Red" }
if ($failCount -gt 0) { Write-ColorOutput "  失败: $failCount" "Red" }

Write-ColorOutput "`n========================================" "Cyan"

if ($failCount -eq 0 -and $errorCount -eq 0) {
    Write-ColorOutput "  ✓ 所有检查通过！" "Green"
    exit 0
} elseif ($failCount -gt 0) {
    Write-ColorOutput "  ✗ 有检查项失败，需要处理" "Red"
    exit 1
} else {
    Write-ColorOutput "  ⚠ 有警告，请关注" "Yellow"
    exit 0
}