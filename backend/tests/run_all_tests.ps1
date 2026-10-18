# AI-NAS Media Manager - 一键测试脚本
# 使用方法：.\run_all_tests.ps1
# 前提：后端服务已启动 (python main.py)

param(
    [string]$ApiBase = "http://localhost:8000"
)

$ErrorActionPreference = "Continue"
$passed = 0
$failed = 0
$token = $null

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AI-NAS Media Manager Test Script V1.0" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

function Test-Endpoint {
    param(
        [string]$name,
        [string]$url,
        [string]$method = "GET",
        [string]$body = $null,
        [string]$token = $null,
        [string]$contentType = "application/json"
    )
    
    try {
        $headers = @{}
        if ($token) { $headers["Authorization"] = "Bearer $token" }
        
        if ($method -eq "GET") {
            $resp = Invoke-RestMethod -Uri $url -Method GET -Headers $headers -TimeoutSec 10 -ErrorAction Stop
        } elseif ($method -eq "POST") {
            if ($contentType -eq "application/x-www-form-urlencoded") {
                $headers["Content-Type"] = $contentType
            }
            $resp = Invoke-RestMethod -Uri $url -Method POST -Headers $headers -Body $body -TimeoutSec 10 -ErrorAction Stop
        }
        
        Write-Host "  [PASS] $name" -ForegroundColor Green
        $script:passed++
        return $resp
    } catch {
        $errMsg = $_.Exception.Message
        if ($errMsg.Length -gt 80) { $errMsg = $errMsg.Substring(0, 80) + "..." }
        Write-Host "  [FAIL] $name" -ForegroundColor Red
        Write-Host "         Error: $errMsg" -ForegroundColor DarkRed
        $script:failed++
        return $null
    }
}

# ============================================
# T0 Environment Check
# ============================================
Write-Host "`n[T0] Environment Check..." -ForegroundColor Yellow

if (Test-Path "..\main.py") {
    Write-Host "  [PASS] Backend code exists (main.py)" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] Backend code missing (main.py)" -ForegroundColor Red
    $failed++
}

if (Test-Path "..\..\frontend\index.html") {
    $htmlContent = Get-Content "..\..\frontend\index.html" -Raw -ErrorAction SilentlyContinue
    if ($htmlContent -match '<nav class="sidebar"') {
        Write-Host "  [PASS] Frontend code exists and complete" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "  [FAIL] Frontend code incomplete (missing sidebar)" -ForegroundColor Red
        $failed++
    }
} else {
    Write-Host "  [FAIL] Frontend code missing (index.html)" -ForegroundColor Red
    $failed++
}

if (Test-Path "..\data\media.db") {
    Write-Host "  [PASS] Database file exists" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [WARN] Database file missing (will be created on first run)" -ForegroundColor Yellow
}

# ============================================
# T1 Backend Service Check
# ============================================
Write-Host "`n[T1] Backend Service Check..." -ForegroundColor Yellow

$healthResp = Test-Endpoint "T1.1 Health Check" "$ApiBase/health" -method "GET"

if ($healthResp -and $healthResp.status -eq "ok") {
    Write-Host "        Backend service running" -ForegroundColor DarkGreen
} else {
    Write-Host "  [CRITICAL] Backend service not running or unreachable!" -ForegroundColor Red
    Write-Host "             Please start backend: python main.py" -ForegroundColor Yellow
}

# ============================================
# T2 API Smoke Test
# ============================================
Write-Host "`n[T2] API Smoke Test..." -ForegroundColor Yellow

# T2.1 Login
Write-Host "  T2.1 Login Test..." -ForegroundColor DarkYellow
$loginBody = "username=admin" + [char]38 + "password=admin123"  # Use ASCII code for & to avoid PS parsing issue
try {
    $loginResp = Invoke-RestMethod -Uri "$ApiBase/api/auth/login" -Method POST -Headers @{"Content-Type"="application/x-www-form-urlencoded"} -Body $loginBody -TimeoutSec 10 -ErrorAction Stop
    if ($loginResp -and $loginResp.access_token) {
        Write-Host "  [PASS] T2.1 Login success" -ForegroundColor Green
        $passed++
        $token = $loginResp.access_token
        Write-Host "         Token: $($token.Substring(0,20))..." -ForegroundColor DarkGray
    } else {
        Write-Host "  [FAIL] T2.1 Login response format error" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "  [FAIL] T2.1 Login failed: $($_.Exception.Message)" -ForegroundColor Red
    $failed++
}

# T2.2-T2.9 Tests with Token
if ($token) {
    Test-Endpoint "T2.2 Get Current User" "$ApiBase/api/auth/me" -token $token | Out-Null
    Test-Endpoint "T2.3 Media List" "$ApiBase/api/media/" -token $token | Out-Null
    Test-Endpoint "T2.4 Device List" "$ApiBase/api/devices/" -token $token | Out-Null
    Test-Endpoint "T2.5 Task List" "$ApiBase/api/tasks/" -token $token | Out-Null
    Test-Endpoint "T2.6 OCR Status" "$ApiBase/api/ocr/status" -token $token | Out-Null
    Test-Endpoint "T2.7 Cloud Backup Status" "$ApiBase/api/cloud/status" -token $token | Out-Null
    Test-Endpoint "T2.8 System Monitor" "$ApiBase/api/monitor/system" -token $token | Out-Null
    Test-Endpoint "T2.9 User List" "$ApiBase/api/auth/users" -token $token | Out-Null
} else {
    Write-Host "  [SKIP] Skipping subsequent API tests (no Token)" -ForegroundColor Yellow
    $failed += 8
}

# ============================================
# T3 Frontend Integration Test Prompt
# ============================================
Write-Host "`n[T3] Frontend Integration Test (Manual)" -ForegroundColor Yellow
Write-Host "  Please visit in browser: $ApiBase" -ForegroundColor Cyan
Write-Host "  Test steps:" -ForegroundColor White
Write-Host "    1. Check if login page displays correctly" -ForegroundColor White
Write-Host "    2. Enter admin/admin123 and click login" -ForegroundColor White
Write-Host "    3. Verify page redirects to main page with sidebar" -ForegroundColor White
Write-Host "    4. Check if all pages switch correctly" -ForegroundColor White
Write-Host "    5. Press F12 and check Console for errors" -ForegroundColor White

# ============================================
# Summary
# ============================================
Write-Host "`n========================================" -ForegroundColor Cyan
$total = $passed + $failed
Write-Host "Test Result: $passed/$total passed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host "========================================" -ForegroundColor Cyan

if ($failed -gt 0) {
    Write-Host "`nSuggestion: Check failed tests, fix and re-run" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "`nAll tests passed! Continue with T3 frontend test." -ForegroundColor Green
    exit 0
}
