#!/bin/bash
# ==============================================================================
#  AI-NAS Media Manager V7.0 - 卸载脚本
#  使用: sudo bash uninstall.sh
# ==============================================================================
set -euo pipefail

APP_NAME="ai-nas"
SERVICE_NAME="ai-nas"
INSTALL_DIR="${INSTALL_DIR:-/opt/$APP_NAME}"
DATA_DIR="${DATA_DIR:-/data/$APP_NAME}"
CONFIG_DIR="${CONFIG_DIR:-/etc/$APP_NAME}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

confirm() {
    echo ""
    echo "!!! 警告: 此操作不可逆 !!!"
    echo ""
    echo "将删除以下内容:"
    echo "  - 安装目录: $INSTALL_DIR"
    echo "  - 数据目录: $DATA_DIR"
    echo "  - 配置目录: $CONFIG_DIR"
    echo "  - systemd 服务: $SERVICE_NAME"
    echo ""
    read -p "输入 'yes' 继续卸载: " ans
    [ "$ans" = "yes" ] || { echo "取消操作"; exit 0; }
}

# 检查 root
[ "$EUID" -ne 0 ] && { log_error "请使用 sudo 运行"; exit 1; }

# 确认
confirm

# 停止并禁用服务
log_warn "停止服务..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl disable "$SERVICE_NAME" 2>/dev/null || true

# 删除服务文件
rm -f "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload

# 删除目录
log_warn "删除安装文件..."
rm -rf "$INSTALL_DIR"
rm -rf "$DATA_DIR"
rm -rf "$CONFIG_DIR"

log_ok "AI-NAS V7.0 已卸载"
echo ""
echo "注意: 如果需要保留数据，请提前备份 $DATA_DIR"
