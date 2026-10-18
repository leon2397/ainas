# ==============================================================================
#  AI-NAS Media Manager - Backup Script
#  备份数据库、配置和日志
# ==============================================================================

param(
    [switch]$Full,           # 完整备份（包含媒体文件）
    [switch]$Quick,          # 快速备份（仅数据库）
    [string]$OutputDir = ".\backups",  # 备份输出目录
    [int]$RetentionDays = 30             # 保留天数
)

$ErrorActionPreference = "Stop"

# 颜色输出函数
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

# 获取项目根目录
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if (-not $ProjectRoot) { $ProjectRoot = "C:\Users\leon23973\.qclaw\workspace\ai-nas-media-manager" }

Write-ColorOutput "========================================" "Cyan"
Write-ColorOutput "  AI-NAS Media Manager - 备份工具" "Cyan"
Write-ColorOutput "========================================`n" "Cyan"

# 创建备份目录
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-ColorOutput "[+] 创建备份目录: $OutputDir" "Green"
}

# 生成备份文件名
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupName = "ai-nas-backup_$timestamp"
$backupPath = Join-Path $OutputDir $backupName

Write-ColorOutput "[*] 备份类型: $(if($Full){'完整备份'}elseif($Quick){'快速备份'}else{'增量备份'})" "Yellow"
Write-ColorOutput "[*] 备份路径: $backupPath`n" "White"

# 开始备份
$startTime = Get-Date
Write-ColorOutput "[1/5] 备份数据库..." "Cyan"

# 停止服务（可选，避免备份时写入冲突）
$stopService = $true
if ($stopService) {
    Write-ColorOutput "    [*] 停止服务中..." "White"
    Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# 数据库路径
$dbPath = Join-Path $ProjectRoot "backend\data\metadata.db"
$dbBackupPath = Join-Path $backupPath "metadata.db"

if (Test-Path $dbPath) {
    New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
    Copy-Item -Path $dbPath -Destination $dbBackupPath -Force
    $dbSize = (Get-Item $dbPath).Length / 1MB
    Write-ColorOutput "    [+] 数据库已备份 ($([math]::Round($dbSize, 2)) MB)" "Green"
} else {
    Write-ColorOutput "    [!] 数据库文件不存在，跳过" "Yellow"
}

Write-ColorOutput "[2/5] 备份配置文件..." "Cyan"
$configFiles = @(
    "backend\config",
    ".env.example",
    "config\*.yaml"
)

foreach ($pattern in $configFiles) {
    $files = Get-ChildItem -Path $ProjectRoot -Filter $pattern -Recurse -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        $relativePath = $file.FullName.Replace($ProjectRoot, "").TrimStart("\")
        $destPath = Join-Path $backupPath $relativePath
        $destDir = Split-Path -Parent $destPath
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
        Copy-Item -Path $file.FullName -Destination $destPath -Force
    }
}
Write-ColorOutput "    [+] 配置文件已备份" "Green"

Write-ColorOutput "[3/5] 备份日志..." "Cyan"
$logPath = Join-Path $ProjectRoot "backend\logs"
$logBackupPath = Join-Path $backupPath "logs"

if (Test-Path $logPath) {
    $destDir = Split-Path -Parent $logBackupPath
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Copy-Item -Path $logPath -Destination $logBackupPath -Recurse -Force
    Write-ColorOutput "    [+] 日志已备份" "Green"
} else {
    Write-ColorOutput "    [!] 日志目录不存在，跳过" "Yellow"
}

# 完整备份时包含媒体文件
if ($Full) {
    Write-ColorOutput "[4/5] 备份媒体文件（完整）..." "Cyan"
    Write-ColorOutput "    [!] 完整备份需要较长时间..." "Yellow"
    
    $mediaPaths = @(
        (Join-Path $ProjectRoot "backend\photo_album"),
        (Join-Path $ProjectRoot "backend\photo_original")
    )
    
    $totalSize = 0
    foreach ($mediaPath in $mediaPaths) {
        if (Test-Path $mediaPath) {
            $size = (Get-ChildItem -Path $mediaPath -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            $totalSize += $size
        }
    }
    
    $sizeGB = [math]::Round($totalSize / 1GB, 2)
    Write-ColorOutput "    [*] 媒体文件总计: $sizeGB GB" "White"
    
    $destMediaPath = Join-Path $backupPath "media"
    New-Item -ItemType Directory -Path $destMediaPath -Force | Out-Null
    
    foreach ($mediaPath in $mediaPaths) {
        if (Test-Path $mediaPath) {
            $relativeName = Split-Path -Leaf $mediaPath
            Copy-Item -Path $mediaPath -Destination (Join-Path $destMediaPath $relativeName) -Recurse -Force
        }
    }
    Write-ColorOutput "    [+] 媒体文件已备份" "Green"
} else {
    Write-ColorOutput "[4/5] 跳过媒体文件（使用 -Full 参数包含）" "Cyan"
}

Write-ColorOutput "[5/5] 创建备份清单..." "Cyan"
$manifest = @{
    "timestamp" = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    "backup_type" = if($Full){"full"}elseif($Quick){"quick"}else{"incremental"}
    "backup_path" = $backupPath
    "files" = @()
} | ConvertTo-Json

$manifestPath = Join-Path $backupPath "manifest.json"
$manifest | Out-File -FilePath $manifestPath -Encoding UTF8

# 计算备份大小
$backupSize = (Get-ChildItem -Path $backupPath -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
$backupSizeMB = [math]::Round($backupSize / 1MB, 2)

Write-ColorOutput "    [+] 清单已创建" "Green"

# 重启服务
if ($stopService) {
    Write-ColorOutput "`n[*] 重启服务..." "White"
    Start-Process python -ArgumentList "main.py" -WorkingDirectory (Join-Path $ProjectRoot "backend") -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# 清理旧备份
Write-ColorOutput "`n[*] 清理超过 $RetentionDays 天的旧备份..." "White"
$oldBackups = Get-ChildItem -Path $OutputDir -Directory | Where-Object {
    $_.CreationTime -lt (Get-Date).AddDays(-$RetentionDays)
}

foreach ($old in $oldBackups) {
    Remove-Item -Path $old.FullName -Recurse -Force
    Write-ColorOutput "    [-] 已删除: $($old.Name)" "Yellow"
}

if ($oldBackups.Count -eq 0) {
    Write-ColorOutput "    [*] 无需清理的旧备份" "White"
}

# 完成
$duration = (Get-Date) - $startTime
Write-ColorOutput "`n========================================" "Green"
Write-ColorOutput "  备份完成！" "Green"
Write-ColorOutput "========================================" "Green"
Write-ColorOutput "  备份大小: $backupSizeMB MB" "White"
Write-ColorOutput "  备份时间: $([math]::Round($duration.TotalSeconds, 1)) 秒" "White"
Write-ColorOutput "  备份位置: $backupPath" "White"
Write-ColorOutput "========================================`n" "Green"

# 返回备份路径供后续使用
return $backupPath