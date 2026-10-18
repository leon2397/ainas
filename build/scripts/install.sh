#!/bin/bash
# AIqizhi One-Click Installer
# Supports: Debian/Ubuntu (DEB), CentOS/RHEL (RPM), Generic Linux
# Usage: ./install.sh [--offline] [--arch arm64|amd64] [--yes]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$(dirname "$SCRIPT_DIR")"
PKG_DIR="$BUILD_DIR/packages"
OFFLINE=0
AUTO_YES=0
ARCH="auto"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --offline) OFFLINE=1; shift ;;
        --yes|-y)  AUTO_YES=1; shift ;;
        --arch)    ARCH="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--offline] [--arch arm64|amd64] [--yes]"
            echo ""
            echo "  --offline    Install from offline package"
            echo "  --arch       Force architecture (default: auto-detect)"
            echo "  --yes        Skip confirmation prompts"
            exit 0 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

# Detect architecture
if [ "$ARCH" = "auto" ]; then
    MACHINE=$(uname -m)
    case $MACHINE in
        aarch64|arm64) ARCH="arm64" ;;
        x86_64|amd64)  ARCH="amd64" ;;
        *) fail "Unsupported architecture: $MACHINE" ;;
    esac
fi

# RPM arch mapping
RPM_ARCH="aarch64"
[ "$ARCH" = "amd64" ] && RPM_ARCH="x86_64"

echo ""
echo -e "${CYAN}"
echo "  ___  _   _  ___   ___ "
echo " / _ \\| \\ | |/ _ \\ / _ \\"
echo "| |_| |  \\| | | | | |_| |"
echo "|  _  | .\` | | |_| |  _| |"
echo "|_| |_|_|\\_|_|\\___/|_|"
echo "     Media Manager"
echo -e "${NC}"
echo ""

info "Architecture:  $ARCH"
info "Offline mode:  $([ $OFFLINE -eq 1 ] && echo 'Yes' || echo 'No')"
echo ""

# Detect distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID="${ID,,}"
    DISTRO_VERSION="${VERSION_ID%%.*}"
    info "Detected: $PRETTY_NAME"
else
    DISTRO_ID="unknown"
    warn "Cannot detect distribution"
fi

# Check root
if [ "$(id -u)" -ne 0 ]; then
    fail "This installer requires root. Run with: sudo $0"
fi

# Confirm
if [ $AUTO_YES -eq 0 ]; then
    echo -e "${YELLOW}This will install AIqizhi Media Manager on this system.${NC}"
    read -p "Continue? [Y/n] " CONFIRM
    [[ "$CONFIRM" =~ ^[Nn] ]] && { echo "Cancelled."; exit 0; }
fi

# Install system dependencies
echo ""
info "Installing system dependencies..."

if [[ "$DISTRO_ID" =~ ^(debian|ubuntu|raspbian)$ ]]; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip python3-venv ffmpeg curl 2>/dev/null
    ok "System dependencies installed (apt)"
elif [[ "$DISTRO_ID" =~ ^(centos|rhel|rocky|almalinux|fedora)$ ]]; then
    if command -v dnf >/dev/null 2>&1; then
        dnf install -y python3 python3-pip python3-virtualenv ffmpeg curl 2>/dev/null
    else
        yum install -y python3 python3-pip python3-virtualenv ffmpeg curl 2>/dev/null
    fi
    ok "System dependencies installed (yum/dnf)"
elif [[ "$DISTRO_ID" =~ ^(kylin|uos)$ ]]; then
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -qq
        apt-get install -y -qq python3 python3-pip python3-venv ffmpeg curl 2>/dev/null
    else
        yum install -y python3 python3-pip python3-virtualenv ffmpeg curl 2>/dev/null
    fi
    ok "System dependencies installed"
else
    warn "Unknown distro ($DISTRO_ID). Please install manually:"
    warn "  python3 >= 3.8, python3-pip, python3-venv, ffmpeg, curl"
fi

# Install package
echo ""
info "Installing AIqizhi package..."

if [ $OFFLINE -eq 1 ]; then
    # Offline install
    OFFLINE_DIR="$PKG_DIR/offline"
    if [[ "$DISTRO_ID" =~ ^(debian|ubuntu|raspbian|kylin|uos)$ ]]; then
        DEB_FILE=$(ls "$OFFLINE_DIR"/aiqizhi_*_${ARCH}.deb 2>/dev/null | head -1)
        if [ -n "$DEB_FILE" ]; then
            dpkg -i "$DEB_FILE"
            ok "DEB package installed: $(basename $DEB_FILE)"
        else
            # Try system deps from offline dir
            for dep in "$OFFLINE_DIR"/system-deps/*.deb; do
                [ -f "$dep" ] && dpkg -i "$dep" 2>/dev/null || true
            done
            DEB_FILE=$(ls "$OFFLINE_DIR"/aiqizhi_*_${ARCH}.deb 2>/dev/null | head -1)
            if [ -n "$DEB_FILE" ]; then
                dpkg -i "$DEB_FILE"
                ok "DEB package installed (with offline deps)"
            else
                fail "No DEB package found in $OFFLINE_DIR"
            fi
        fi
    elif [[ "$DISTRO_ID" =~ ^(centos|rhel|rocky|almalinux|fedora)$ ]]; then
        RPM_FILE=$(ls "$OFFLINE_DIR"/aiqizhi-*-${RPM_ARCH}.rpm 2>/dev/null | head -1)
        if [ -n "$RPM_FILE" ]; then
            rpm -ivh "$RPM_FILE"
            ok "RPM package installed: $(basename $RPM_FILE)"
        else
            fail "No RPM package found in $OFFLINE_DIR"
        fi
    fi
else
    # Online install from pre-built package
    if [[ "$DISTRO_ID" =~ ^(debian|ubuntu|raspbian|kylin|uos)$ ]] || [ "$DISTRO_ID" = "unknown" ]; then
        DEB_FILE="$PKG_DIR/aiqizhi_2.0.0_${ARCH}.deb"
        if [ -f "$DEB_FILE" ]; then
            dpkg -i "$DEB_FILE"
            ok "DEB package installed"
        else
            fail "Package not found: $DEB_FILE. Run build-deb.sh first."
        fi
    elif [[ "$DISTRO_ID" =~ ^(centos|rhel|rocky|almalinux|fedora)$ ]]; then
        RPM_FILE="$PKG_DIR/aiqizhi-2.0.0-1.${RPM_ARCH}.rpm"
        if [ -f "$RPM_FILE" ]; then
            rpm -ivh "$RPM_FILE"
            ok "RPM package installed"
        else
            fail "Package not found: $RPM_FILE. Run build-rpm.sh first."
        fi
    fi
fi

# Health check
echo ""
info "Running health check..."
sleep 3

HEALTH_OK=0
if command -v curl >/dev/null 2>&1; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:18000/api/monitor/status 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        ok "API is responding (HTTP $HTTP_CODE)"
        HEALTH_OK=1
    else
        warn "API returned HTTP $HTTP_CODE"
    fi
fi

SVC_STATUS=$(systemctl is-active aiqizhi 2>/dev/null || echo "inactive")
if [ "$SVC_STATUS" = "active" ]; then
    ok "Systemd service is running"
    HEALTH_OK=1
else
    warn "Systemd service status: $SVC_STATUS"
fi

echo ""
if [ $HEALTH_OK -eq 1 ]; then
    echo -e "${GREEN}=== AIqizhi Installation Successful! ===${NC}"
else
    echo -e "${YELLOW}=== AIqizhi Installation Completed (with warnings) ===${NC}"
    echo "Check logs: journalctl -u aiqizhi -n 50"
fi
echo ""

SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_SERVER_IP")
echo -e "  Access: ${CYAN}http://${SERVER_IP}:18000${NC}"
echo "  Config: /etc/aiqizhi/config.yaml"
echo "  Logs:   journalctl -u aiqizhi -f"
echo ""
