#!/bin/bash
# AIqizhi Health Check
# Usage: ./health-check.sh [--json]
set -e

JSON_OUTPUT=0
while [[ $# -gt 0 ]]; do
    case $1 in
        --json) JSON_OUTPUT=1; shift ;;
        -h|--help) echo "Usage: $0 [--json]"; exit 0 ;;
    esac
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

pass_check() { [ $JSON_OUTPUT -eq 1 ] && echo "PASS:$1" || echo -e "  ${GREEN}PASS${NC} $1"; }
fail_check() { [ $JSON_OUTPUT -eq 1 ] && echo "FAIL:$1" || echo -e "  ${RED}FAIL${NC} $1"; }
warn_check() { [ $JSON_OUTPUT -eq 1 ] && echo "WARN:$1" || echo -e "  ${YELLOW}WARN${NC} $1"; }

if [ $JSON_OUTPUT -eq 0 ]; then
    echo -e "${CYAN}=== AIqizhi Health Check ===${NC}"
    echo ""
fi

TOTAL=0
PASS=0
FAIL=0

# 1. Systemd service
TOTAL=$((TOTAL+1))
SVC_STATUS=$(systemctl is-active aiqizhi 2>/dev/null || echo "unknown")
if [ "$SVC_STATUS" = "active" ]; then
    pass_check "Systemd service: active"
    PASS=$((PASS+1))
else
    fail_check "Systemd service: $SVC_STATUS"
    FAIL=$((FAIL+1))
fi

# 2. Port listening
TOTAL=$((TOTAL+1))
if ss -tlnp 2>/dev/null | grep -q ":18000 "; then
    pass_check "Port 18000: listening"
    PASS=$((PASS+1))
elif netstat -tlnp 2>/dev/null | grep -q ":18000 "; then
    pass_check "Port 18000: listening"
    PASS=$((PASS+1))
else
    fail_check "Port 18000: not listening"
    FAIL=$((FAIL+1))
fi

# 3. API response
TOTAL=$((TOTAL+1))
if command -v curl >/dev/null 2>&1; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:18000/api/monitor/status 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        pass_check "API /monitor/status: HTTP $HTTP_CODE"
        PASS=$((PASS+1))
    else
        fail_check "API /monitor/status: HTTP $HTTP_CODE"
        FAIL=$((FAIL+1))
    fi
else
    warn_check "API check: curl not available"
fi

# 4. Login API
TOTAL=$((TOTAL+1))
if command -v curl >/dev/null 2>&1; then
    LOGIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -X POST http://localhost:18000/api/auth/login         -H "Content-Type: application/x-www-form-urlencoded"         -d "username=admin&password=test" 2>/dev/null || echo "000")
    if [ "$LOGIN_CODE" = "401" ] || [ "$LOGIN_CODE" = "200" ]; then
        pass_check "API /auth/login: HTTP $LOGIN_CODE (auth working)"
        PASS=$((PASS+1))
    else
        fail_check "API /auth/login: HTTP $LOGIN_CODE"
        FAIL=$((FAIL+1))
    fi
fi

# 5. Disk space
TOTAL=$((TOTAL+1))
DATA_DIR="/var/lib/aiqizhi"
if [ -d "$DATA_DIR" ]; then
    DISK_AVAIL=$(df -h "$DATA_DIR" --output=avail 2>/dev/null | tail -1 | tr -d ' ')
    if [ -n "$DISK_AVAIL" ]; then
        pass_check "Disk space available: $DISK_AVAIL"
        PASS=$((PASS+1))
    else
        warn_check "Disk space: unable to check"
    fi
else
    warn_check "Data directory not found: $DATA_DIR"
fi

# 6. Database
TOTAL=$((TOTAL+1))
DB_PATH="/var/lib/aiqizhi/database/aiqizhi.db"
if [ -f "$DB_PATH" ]; then
    DB_SIZE=$(du -h "$DB_PATH" | awk '{print $1}')
    pass_check "Database exists: $DB_SIZE"
    PASS=$((PASS+1))
elif [ -f "/opt/aiqizhi/backend/data/aiqizhi.db" ]; then
    DB_SIZE=$(du -h "/opt/aiqizhi/backend/data/aiqizhi.db" | awk '{print $1}')
    pass_check "Database exists (legacy path): $DB_SIZE"
    PASS=$((PASS+1))
else
    fail_check "Database not found"
    FAIL=$((FAIL+1))
fi

# 7. Python venv
TOTAL=$((TOTAL+1))
if [ -f "/opt/aiqizhi/backend/venv/bin/python" ]; then
    PY_VER=$("/opt/aiqizhi/backend/venv/bin/python" --version 2>&1 || echo "unknown")
    pass_check "Python venv: $PY_VER"
    PASS=$((PASS+1))
else
    fail_check "Python venv not found"
    FAIL=$((FAIL+1))
fi

# 8. Key dependencies
TOTAL=$((TOTAL+1))
if [ -f "/opt/aiqizhi/backend/venv/bin/python" ]; then
    MISSING=$("/opt/aiqizhi/backend/venv/bin/python" -c "
import importlib
mods = ['fastapi','uvicorn','pydantic','aiosqlite','pillow','yaml']
missing = [m for m in mods if importlib.util.find_spec(m) is None]
print(','.join(missing) if missing else 'OK')
" 2>/dev/null || echo "ERROR")
    if [ "$MISSING" = "OK" ]; then
        pass_check "Python dependencies: all present"
        PASS=$((PASS+1))
    else
        warn_check "Python dependencies missing: $MISSING"
    fi
else
    fail_check "Python deps: venv not found"
    FAIL=$((FAIL+1))
fi

# Summary
echo ""
if [ $JSON_OUTPUT -eq 0 ]; then
    echo "----------------------------------------"
    echo -e "  Total: $TOTAL  ${GREEN}Pass: $PASS${NC}  ${RED}Fail: $FAIL${NC}"
    echo "----------------------------------------"
    if [ $FAIL -eq 0 ]; then
        echo -e "${GREEN}System is healthy!${NC}"
    else
        echo -e "${RED}$FAIL check(s) failed. Check logs: journalctl -u aiqizhi -n 50${NC}"
    fi
else
    echo "{"total":$TOTAL,"pass":$PASS,"fail":$FAIL}"
fi
echo ""
