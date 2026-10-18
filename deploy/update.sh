#!/bin/bash
# ==============================================================================
#  AI-NAS Media Manager V7.0 - 升级脚本
#  支持: 本地包升级、URL 下载升级、自动回滚
#  使用: sudo bash update.sh <pkg.tar.gz> | --url <url> | --rollback
# ==============================================================================
set -euo pipefail

APP_NAME="ai-nas"
SERVICE_NAME="ai-nas"
INSTALL_DIR="${INSTALL_DIR:-/opt/$APP_NAME}"
DATA_DIR="${DATA_DIR:-/data/$APP_NAME}"
BACKUP_DIR="$DATA_DIR/backup"
UPDATE_TMP="/tmp/ai-nas-update"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

get_cur_ver() {
    [ -f "$DATA_DIR/.version" ] && head -1 "$DATA_DIR/.version" || echo "unknown"
}

get_pkg_ver() {
    basename "$1" .tar.gz | grep -oP 'v?[0-9]+\.[0-9]+\.[0-9]+' | head -1
}

do_rollback() {
    log_warn "执行自动回滚..."
    local info="$BACKUP_DIR/rollback-info"

    [ ! -f "$info" ] && { log_error "找不到备份信息"; exit 1; }
    source "$info"

    systemctl stop "$SERVICE_NAME" 2>/dev/null || fuser -k 8000/tcp 2>/dev/null || true

    [ -d "$BACKUP_PATH/backend" ] && cp -r "$BACKUP_PATH/backend" "$INSTALL_DIR/backend" || true
    [ -d "$BACKUP_PATH/frontend" ] && cp -r "$BACKUP_PATH/frontend" "$INSTALL_DIR/frontend" || true

    echo "$PREV_VERSION" > "$DATA_DIR/.version"

    systemctl start "$SERVICE_NAME" 2>/dev/null || true
    sleep 3

    if curl -sf "http://127.0.0.1:8000/health" &>/dev/null; then
        log_ok "回滚成功: $PREV_VERSION"
    else
        log_error "健康检查失败，请手动检查"
        exit 1
    fi
}

do_update() {
    local pkg="$1"
    local pkg_ver=$(get_pkg_ver "$pkg")
    local cur_ver=$(get_cur_ver)

    log_info "当前版本: $cur_ver -> 新版本: $pkg_ver"

    # 校验
    if [ -f "${pkg}.sha256" ]; then
        sha256sum -c "${pkg}.sha256" || { log_warn "校验失败，继续升级"; }
    fi

    # 备份
    log_info "备份当前版本..."
    local bp="$BACKUP_DIR/${cur_ver}-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$bp"
    cp -r "$INSTALL_DIR/backend" "$bp/" 2>/dev/null || true
    cp -r "$INSTALL_DIR/frontend" "$bp/" 2>/dev/null || true

    echo "PREV_VERSION=$cur_ver" > "$BACKUP_DIR/rollback-info"
    echo "BACKUP_PATH=$bp" >> "$BACKUP_DIR/rollback-info"
    echo "UPDATE_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$BACKUP_DIR/rollback-info"

    # 解压
    log_info "解压更新包..."
    rm -rf "$UPDATE_TMP"
    mkdir -p "$UPDATE_TMP"
    tar -xzf "$pkg" -C "$UPDATE_TMP"

    # 停止服务
    log_info "停止服务..."
    systemctl stop "$SERVICE_NAME" 2>/dev/null || fuser -k 8000/tcp 2>/dev/null || true

    # 应用更新
    log_info "应用更新..."
    [ -d "$UPDATE_TMP/backend" ] && cp -r "$UPDATE_TMP/backend"/* "$INSTALL_DIR/backend/" || true
    [ -d "$UPDATE_TMP/frontend" ] && cp -r "$UPDATE_TMP/frontend"/* "$INSTALL_DIR/frontend/" || true

    # 数据库迁移
    if [ -d "$UPDATE_TMP/migrations" ] && [ -f "$UPDATE_TMP/migrations/run.py" ]; then
        log_info "执行数据库迁移..."
        source "$INSTALL_DIR/venv/bin/activate" 2>/dev/null || true
        python3 "$UPDATE_TMP/migrations/run.py" "$DATA_DIR/metadata.db" 2>/dev/null || true
        deactivate 2>/dev/null || true
    fi

    # 更新版本号
    echo "$pkg_ver" > "$DATA_DIR/.version"

    # 启动服务
    log_info "启动服务..."
    systemctl start "$SERVICE_NAME" 2>/dev/null || true
    sleep 3

    # 健康检查
    if curl -sf "http://127.0.0.1:8000/health" &>/dev/null; then
        log_ok "升级成功: $pkg_ver"
    else
        log_warn "健康检查失败，尝试回滚..."
        do_rollback
    fi

    rm -rf "$UPDATE_TMP"
}

show_usage() {
    echo "AI-NAS V7.0 升级脚本"
    echo ""
    echo "用法:"
    echo "  sudo bash update.sh <pkg.tar.gz>     # 本地包升级"
    echo "  sudo bash update.sh --url <URL>      # 从 URL 下载并升级"
    echo "  sudo bash update.sh --check          # 检查当前版本"
    echo "  sudo bash update.sh --rollback       # 回滚到上一个版本"
    echo ""
    echo "当前版本: $(get_cur_ver)"
}

main() {
    [ "$EUID" -ne 0 ] && { log_error "请使用 sudo 运行"; exit 1; }

    case "${1:-}" in
        --rollback)
            do_rollback
            ;;
        --check)
            log_info "当前版本: $(get_cur_ver)"
            ;;
        --url)
            [ -z "${2:-}" ] && { log_error "缺少 URL 参数"; exit 1; }
            local pkg="/tmp/ai-nas-$(basename "$2")"
            log_info "下载: $2"
            curl -fSL "$2" -o "$pkg" || { log_error "下载失败"; exit 1; }
            do_update "$pkg"
            ;;
        "")
            show_usage
            ;;
        *)
            if [ -f "$1" ]; then
                do_update "$1"
            else
                log_error "未知参数或文件不存在: $1"
                exit 1
            fi
            ;;
    esac
}

main "$@"
