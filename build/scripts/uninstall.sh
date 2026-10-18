#!/bin/bash
# AIqizhi Uninstaller
# Usage: ./uninstall.sh [--purge] [--yes]
set -e

PURGE=0
AUTO_YES=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

while [[ $# -gt 0 ]]; do
    case $1 in
        --purge)  PURGE=1; shift ;;
        --yes|-y) AUTO_YES=1; shift ;;
        -h|--help)
            echo "Usage: $0 [--purge] [--yes]"
            echo ""
            echo "  --purge    Remove all data and config"
            echo "  --yes      Skip confirmation"
            exit 0 ;;
    esac
done

if [ "$(id -u)" -ne 0 ]; then
    fail "Root required. Run: sudo $0"
fi

echo ""
warn "This will uninstall AIqizhi Media Manager."
if [ $PURGE -eq 1 ]; then
    warn "PURGE mode: ALL data, config and logs will be permanently deleted!"
fi
echo ""

if [ $AUTO_YES -eq 0 ]; then
    read -p "Are you sure? [y/N] " CONFIRM
    [[ ! "$CONFIRM" =~ ^[Yy] ]] && { echo "Cancelled."; exit 0; }
fi

# Stop service
info "Stopping service..."
systemctl stop aiqizhi 2>/dev/null || true
systemctl disable aiqizhi 2>/dev/null || true
ok "Service stopped"

# Remove package
info "Removing package..."
if command -v dpkg >/dev/null 2>&1 && dpkg -l aiqizhi >/dev/null 2>&1; then
    if [ $PURGE -eq 1 ]; then
        dpkg --purge aiqizhi
        ok "DEB package purged"
    else
        dpkg --remove aiqizhi
        ok "DEB package removed"
    fi
elif command -v rpm >/dev/null 2>&1 && rpm -q aiqizhi >/dev/null 2>&1; then
    rpm -e aiqizhi
    ok "RPM package removed"
else
    warn "No package manager entry found, performing manual cleanup..."

    # Manual cleanup
    rm -f /etc/systemd/system/aiqizhi.service
    rm -f /etc/logrotate.d/aiqizhi
    rm -rf /opt/aiqizhi
    systemctl daemon-reload
    ok "Manual cleanup done"
fi

# Purge data
if [ $PURGE -eq 1 ]; then
    info "Purging data..."
    if [ -d /var/lib/aiqizhi ]; then
        rm -rf /var/lib/aiqizhi
        ok "Data directory removed"
    fi
    if [ -d /var/log/aiqizhi ]; then
        rm -rf /var/log/aiqizhi
        ok "Log directory removed"
    fi
    if [ -d /etc/aiqizhi ]; then
        rm -rf /etc/aiqizhi
        ok "Config directory removed"
    fi

    # Remove user
    if id aiqizhi >/dev/null 2>&1; then
        userdel aiqizhi 2>/dev/null || true
        ok "System user removed"
    fi
fi

systemctl daemon-reload 2>/dev/null || true

echo ""
echo -e "${GREEN}=== AIqizhi Uninstalled ===${NC}"
if [ $PURGE -eq 0 ]; then
    echo "Note: Data preserved in /var/lib/aiqizhi"
    echo "      Use --purge to remove all data"
fi
echo ""
