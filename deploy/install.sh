#!/bin/bash
# ==============================================================================
#  AI-NAS Media Manager V7.0 - 一键安装脚本
#  支持: x86_64 / aarch64 (ARM) 自动检测
#  适用: Linux (Ubuntu/Debian/CentOS/群晖/威联通/树莓派)
#  使用: sudo bash install.sh
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

INSTALL_DIR="${INSTALL_DIR:-/opt/ai-nas}"
DATA_DIR="${DATA_DIR:-/data/ai-nas}"
PORT="${PORT:-8000}"
ARCH=""; IS_ARM=false; PYTHON_CMD=""

detect_arch() {
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64|amd64)  ARCH="x86_64";  log_ok "架构: x86_64 (Intel/AMD)" ;;
        aarch64|arm64) ARCH="aarch64"; IS_ARM=true; log_ok "架构: aarch64 (ARM 64位)" ;;
        armv7l|armhf)  ARCH="armv7l";  IS_ARM=true; log_warn "架构: ARM 32位，部分功能受限" ;;
        *) log_error "不支持的架构: $ARCH"; exit 1 ;;
    esac
}

detect_os() {
    if [ -f /etc/os-release ]; then . /etc/os-release; OS_NAME="$PRETTY_NAME"; else OS_NAME="Unknown Linux"; fi
    [ -f /etc/synoinfo.conf ] && log_ok "检测到群晖 Synology DSM"
    log_ok "系统: $OS_NAME"
}

detect_python() {
    for py in python3.12 python3.11 python3.13 python3 python; do
        if command -v $py &>/dev/null; then
            ver=$($py -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            if [ "${ver%%.*}" -ge 3 ] && [ "${ver#*.}" -ge 9 ] 2>/dev/null; then
                PYTHON_CMD="$py"
                log_ok "Python: $($py --version 2>&1)"
                return
            fi
        fi
    done
    log_error "未找到 Python 3.9+，请先安装"
    exit 1
}

check_root() { [ "$(id -u)" -ne 0 ] && { log_error "请用 sudo 运行: sudo bash install.sh"; exit 1; }; }

create_dirs() {
    mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$DATA_DIR/media" "$DATA_DIR/thumbnails" "$DATA_DIR/cache"
    chmod -R 755 "$INSTALL_DIR" "$DATA_DIR"
    log_ok "目录创建完成"
}

install_system_deps() {
    log_info "安装系统依赖..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq
        apt-get install -y -qq curl sqlite3 ffmpeg libsqlite3-dev
        [ "$IS_ARM" = true ] && apt-get install -y -qq libgl1-mesa-glx libglib2.0-0 libgomp1 libraw-dev 2>/dev/null || \
                                  apt-get install -y -qq libgl1 libglib2.0-0 libgomp1
    elif command -v yum &>/dev/null; then
        yum install -y -q curl sqlite mesa-libGL glib2 libgomp 2>/dev/null || true
        # ffmpeg 可选，从 epel 或第三方源安装
        yum install -y -q ffmpeg 2>/dev/null || log_warn "ffmpeg 安装失败（可选依赖）"
    elif command -v dnf &>/dev/null; then
        dnf install -y -q curl sqlite mesa-libGL glib2 libgomp 2>/dev/null || true
        dnf install -y -q ffmpeg 2>/dev/null || log_warn "ffmpeg 安装失败（可选依赖）"
    fi
    log_ok "系统依赖完成"
}

create_venv() {
    [ -d "$INSTALL_DIR/venv" ] && { log_warn "虚拟环境已存在"; return; }
    $PYTHON_CMD -m venv "$INSTALL_DIR/venv"
    log_ok "虚拟环境创建完成"
}

install_python_deps() {
    log_info "安装 Python 依赖..."
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --upgrade pip -q

    if [ "$IS_ARM" = true ]; then
        log_info "ARM 架构，使用 opencv-python-headless..."
        pip install opencv-python-headless==4.10.0.84 -q 2>/dev/null || pip install opencv-python-headless -q
    fi

    # 安装核心依赖（版本锁定）
    pip install fastapi==0.115.5 uvicorn[standard]==0.32.0 websockets==13.1 \
        python-multipart==0.0.17 pydantic==2.9.2 pydantic-settings==2.6.1 \
        aiosqlite==0.20.0 chromadb==0.5.5 pillow==11.0.0 \
        numpy==1.26.4 rawpy==0.21.0 onnxruntime==1.24.4 \
        scikit-learn==1.5.2 pyyaml==6.0.2 apscheduler==3.11.0 \
        requests==2.32.3 python-dotenv==1.0.1 psutil==6.1.0 \
        paramiko==3.5.0 smbprotocol==1.14.0 aiohttp==3.11.2 \
        loguru==0.7.2 python-jose==3.3.0 passlib==1.7.4 -q 2>&1 | tail -3

    deactivate
    log_ok "Python 依赖安装完成"
}

install_code() {
    log_info "安装 AI-NAS V7.0 代码..."

    # 检查本地代码
    if [ -f "$(dirname "$0")/../backend/main.py" ]; then
        SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
        cp -r "$SRC_DIR/backend" "$INSTALL_DIR/"
        cp -r "$SRC_DIR/frontend" "$INSTALL_DIR/" 2>/dev/null || true
        cp -r "$SRC_DIR/config" "$INSTALL_DIR/" 2>/dev/null || true
        log_ok "代码安装完成 (本地目录)"
    elif [ -f "$(dirname "$0")/backend/main.py" ]; then
        SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
        cp -r "$SRC_DIR/backend" "$INSTALL_DIR/"
        cp -r "$SRC_DIR/frontend" "$INSTALL_DIR/" 2>/dev/null || true
        cp -r "$SRC_DIR/config" "$INSTALL_DIR/" 2>/dev/null || true
        log_ok "代码安装完成 (本地目录)"
    else
        log_error "请将 AI-NAS 代码放在 install.sh 同级或上级目录"
        exit 1
    fi
}

configure() {
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        local jwt_secret=$(head -c 32 /dev/urandom 2>/dev/null | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)
        cat > "$INSTALL_DIR/.env" << EOF
# AI-NAS V7.0 环境变量配置
AI_NAS_JWT_SECRET=${jwt_secret}
AI_NAS_TOKEN_EXPIRE_HOURS=24
AI_NAS_CORS_ORIGINS=*
LOG_LEVEL=INFO
BACKEND_PORT=${PORT}
NAS_PATH=${DATA_DIR}/media
EOF
        log_ok "配置文件已生成"
    else
        log_warn "配置文件已存在，跳过"
    fi
}

init_db() {
    log_info "初始化数据库..."
    source "$INSTALL_DIR/venv/bin/activate"
    cd "$INSTALL_DIR/backend"

    # 运行数据库迁移
    if [ -f "migrations/run.py" ]; then
        python migrations/run.py --init 2>/dev/null || true
    fi

    deactivate
    log_ok "数据库初始化完成"
}

install_service() {
    log_info "注册 systemd 服务..."

    cat > /etc/systemd/system/ai-nas.service << EOF
[Unit]
Description=AI-NAS Media Manager V7.0
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}/backend
Environment="PATH=${INSTALL_DIR}/venv/bin"
Environment="PYTHONPATH=${INSTALL_DIR}/backend"
ExecStart=${INSTALL_DIR}/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port ${PORT}
Restart=always
RestartSec=10
StandardOutput=append:${DATA_DIR}/logs/ai-nas.log
StandardError=append:${DATA_DIR}/logs/ai-nas-error.log

[Install]
WantedBy=multi-user.target
EOF

    mkdir -p "${DATA_DIR}/logs"
    systemctl daemon-reload
    systemctl enable ai-nas 2>/dev/null || true
    log_ok "服务已注册"
}

start_service() {
    log_info "启动服务..."
    systemctl start ai-nas
    sleep 3

    if systemctl is-active --quiet ai-nas; then
        log_ok "服务启动成功"
    else
        log_error "服务启动失败"
        log_info "查看日志: journalctl -u ai-nas -n 50"
        exit 1
    fi
}

health_check() {
    local ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
    local url="http://${ip}:${PORT}/health"

    if curl -sf --connect-timeout 5 "$url" &>/dev/null; then
        echo ""
        echo "=========================================="
        log_ok "AI-NAS V7.0 安装成功！"
        echo "=========================================="
        echo ""
        echo "  访问地址: http://${ip}:${PORT}"
        echo "  API文档:  http://${ip}:${PORT}/docs"
        echo ""
        echo "  管理命令:"
        echo "    启动:   sudo systemctl start ai-nas"
        echo "    停止:   sudo systemctl stop ai-nas"
        echo "    重启:   sudo systemctl restart ai-nas"
        echo "    日志:   sudo journalctl -u ai-nas -f"
        echo ""
    else
        log_warn "健康检查未通过"
        log_info "查看日志: journalctl -u ai-nas -n 50"
    fi
}

main() {
    echo ""
    echo "=============================================="
    echo "   AI-NAS Media Manager V7.0 一键安装脚本"
    echo "   支持 x86_64 / aarch64 / armv7l"
    echo "=============================================="
    echo ""

    check_root
    detect_arch
    detect_os
    detect_python
    create_dirs
    install_system_deps
    create_venv
    install_python_deps
    install_code
    configure
    init_db
    install_service
    start_service
    health_check

    echo ""
    echo "=============================================="
    log_ok "安装完成！"
    echo "=============================================="
}

main "$@"
