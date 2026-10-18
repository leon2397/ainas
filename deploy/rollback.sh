#!/bin/bash
# ==============================================================================
#  AI-NAS Media Manager V7.0 - 手动回滚脚本
#  使用: sudo bash rollback.sh [backup_path]
# ==============================================================================
set -euo pipefail

APP_NAME="ai-nas"
SERVICE_NAME="ai-nas"
INSTALL_DIR="${INSTALL_DIR:-/opt/$APP_NAME}"
DATA_DIR="${DATA_DIR:-/data/$APP_NAME}"
BACKUP_DIR="$DATA_DIR/backup"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

list_backups() {
    echo "可用备份:"
    ls -dt "$BACKUP_DIR"/*/ 2>/dev/null | head -10 | while read d; do
        local name=$(basename "$d")
        local time=$(grep UPDATE_TIME "$d/rollback-info" 2>/dev/null | cut -d= -f2 || echo "未知")
        echo "  $name  ($time)"
    done || echo "  (无备份)"
}

do_rollback() {
    local bp="${1:-$(ls -dt "$BACKUP_DIR"/*/ 2>/dev/null | head -1)}"

    [ ! -d "$bp" ] && { log_error "备份不存在: $bp"; list_backups; exit 1; }

    source "$bp/rollback-info" 2>/dev/null || true
    local prev="${PREV_VERSION:-$(basename $bp)}"

    echo ""
    echo "!!! 即将回滚版本 !!!"
    echo "    当前: $(cat $DATA_DIR/.version 2>/dev/null || echo 'unknown')"
    echo "    目标: $prev"
    echo ""
    read -p "输入 'rollback' 确认回滚: " ans
    [ "$ans" = "rollback" ] || { echo "取消操作"; exit 0; }

    log_info "停止服务..."
    systemctl stop "$SERVICE_NAME" 2>/dev/null || fuser -k 8000/tcp 2>/dev/null || true

    log_info "恢复备份..."
    rm -rf "$INSTALL_DIR/backend" "$INSTALL_DIR/frontend" 2>/dev/null || true
    [ -d "$bp/backend" ] && cp -r "$bp/backend" "$INSTALL_DIR/backend"
    [ -d "$bp/frontend" ] && cp -r "$bp/frontend" "$INSTALL_DIR/frontend"

    echo "$prev" > "$DATA_DIR/.version"

    log_info "启动服务..."
    systemctl start "$SERVICE_NAME" 2>/dev/null || true
    sleep 3

    if curl -sf "http://127.0.0.1:8000/health" &>/dev/null; then
        log_ok "回滚成功: $prev"
    else
        log_error "健康检查失败，请手动检查"
        exit 1
    fi
}

# 主入口
[ "$EUID" -ne 0 ] && { log_error "请使用 sudo 运行"; exit 1; }

if [ -z "${1:-}" ]; then
    list_backups
    echo ""
    echo "用法: sudo bash rollback.sh [backup_path]"
    exit 0
fi

do_rollback "$1"
