#!/bin/bash
# ==============================================================================
#  AI-NAS Media Manager V7.0 - 健康检查脚本
#  适用: systemd Watchdog / cron 定时检查
#  使用: bash check-health.sh
# ==============================================================================

APP_NAME="ai-nas"
SERVICE_NAME="ai-nas"
DATA_DIR="${DATA_DIR:-/data/$APP_NAME}"
PORT="${PORT:-8000}"

# 获取 IP
get_ip() {
    hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1"
}

# 检查 HTTP 接口
check_http() {
    curl -sf "http://$(get_ip):$PORT/health" &>/dev/null
}

# 检查磁盘空间
check_disk() {
    local usage=$(df "$DATA_DIR" 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//')
    [ "${usage:-0}" -lt 95 ]
}

# 检查数据库
check_db() {
    local db_file="$DATA_DIR/metadata.db"
    [ -f "$db_file" ] || return 0  # 数据库不存在视为正常（首次安装）
    sqlite3 "$db_file" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"
}

# 主检查
status=0

# 检查进程
if ! systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null && ! pgrep -f "uvicorn main:app" &>/dev/null; then
    echo "[ERROR] 服务进程未运行"
    status=2
fi

# 检查 HTTP
if ! check_http; then
    echo "[ERROR] HTTP 健康检查失败"
    status=2
fi

# 检查磁盘
if ! check_disk; then
    echo "[WARN] 磁盘空间不足 (< 5%)"
    status=1
fi

# 检查数据库
if ! check_db; then
    echo "[WARN] 数据库完整性检查异常"
    status=1
fi

# 结果
if [ $status -eq 0 ]; then
    echo "[OK] AI-NAS V7.0 健康"
fi

exit $status
