#!/bin/bash
# AIqizhi Offline Package Builder
# Creates a self-contained tar.gz for air-gapped installation
# Usage: ./build-offline.sh [--arch arm64|amd64]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$(dirname "$SCRIPT_DIR")"
PKG_DIR="$BUILD_DIR/packages"
ARCH="arm64"

while [[ $# -gt 0 ]]; do
    case $1 in
        --arch) ARCH="$2"; shift 2 ;;
        -h|--help) echo "Usage: $0 [--arch arm64|amd64]"; exit 0 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

RPM_ARCH="aarch64"
[ "$ARCH" = "amd64" ] && RPM_ARCH="x86_64"

VERSION="2.0.0"
OFFLINE_NAME="aiqizhi-${VERSION}-offline-${ARCH}"
OFFLINE_DIR=$(mktemp -d)
trap "rm -rf $OFFLINE_DIR" EXIT

echo "=== Building Offline Package: $OFFLINE_NAME ==="

# Step 1: Download Python wheels
echo "[1/4] Downloading Python wheels..."
mkdir -p "$OFFLINE_DIR/python-wheels"
if [ -f "$BUILD_DIR/../../backend/requirements.txt" ]; then
    pip download         -r "$BUILD_DIR/../../backend/requirements.txt"         -d "$OFFLINE_DIR/python-wheels"         --python-version 38         --only-binary=:all:         --platform manylinux2014_${RPM_ARCH} 2>/dev/null || {
        pip download             -r "$BUILD_DIR/../../backend/requirements.txt"             -d "$OFFLINE_DIR/python-wheels" 2>/dev/null || true
    }
fi
WHEEL_COUNT=$(ls "$OFFLINE_DIR/python-wheels" 2>/dev/null | wc -l)
echo "  Downloaded $WHEEL_COUNT wheel files"

# Step 2: Copy package
echo "[2/4] Copying package..."
mkdir -p "$OFFLINE_DIR/package"
if [ -f "$PKG_DIR/aiqizhi_${VERSION}_${ARCH}.deb" ]; then
    cp "$PKG_DIR/aiqizhi_${VERSION}_${ARCH}.deb" "$OFFLINE_DIR/package/"
    echo "  DEB package copied"
fi
if [ -f "$PKG_DIR/aiqizhi-${VERSION}-1.${RPM_ARCH}.rpm" ]; then
    cp "$PKG_DIR/aiqizhi-${VERSION}-1.${RPM_ARCH}.rpm" "$OFFLINE_DIR/package/"
    echo "  RPM package copied"
fi

# Step 3: Create offline install script
echo "[3/4] Creating offline install script..."
cat > "$OFFLINE_DIR/install-offline.sh" << 'OFFLINE_EOF'
#!/bin/bash
# AIqizhi Offline Installer
set -e
OFFLINE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== AIqizhi Offline Installation ==="

# Detect distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO="${ID,,}"
else
    DISTRO="unknown"
fi

# Install system deps from offline cache
if [ -d "$OFFLINE_DIR/system-deps" ]; then
    echo "Installing system dependencies..."
    if [[ "$DISTRO" =~ ^(debian|ubuntu|raspbian)$ ]]; then
        dpkg -i "$OFFLINE_DIR/system-deps"/*.deb 2>/dev/null || true
    elif [[ "$DISTRO" =~ ^(centos|rhel|rocky|almalinux|fedora)$ ]]; then
        rpm -ivh "$OFFLINE_DIR/system-deps"/*.rpm 2>/dev/null || true
    fi
fi

# Install pip wheels offline
if [ -d "$OFFLINE_DIR/python-wheels" ]; then
    echo "Installing Python dependencies offline..."
    python3 -m venv /opt/aiqizhi/backend/venv 2>/dev/null || true
    /opt/aiqizhi/backend/venv/bin/pip install --no-index         --find-links="$OFFLINE_DIR/python-wheels"         -r "$OFFLINE_DIR/../backend/requirements.txt" 2>/dev/null || true
fi

# Install package
echo "Installing AIqizhi package..."
if [ -f "$OFFLINE_DIR/package/aiqizhi_"*"_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')".deb ]; then
    dpkg -i "$OFFLINE_DIR/package/"*.deb
elif [ -f "$OFFLINE_DIR/package/"*.rpm ]; then
    rpm -ivh "$OFFLINE_DIR/package/"*.rpm
fi

echo "=== Installation Complete ==="
OFFLINE_EOF
chmod 0755 "$OFFLINE_DIR/install-offline.sh"

# Step 4: Package everything
echo "[4/4] Creating tarball..."
chmod 0755 "$OFFLINE_DIR/install-offline.sh"
OUTPUT="$PKG_DIR/${OFFLINE_NAME}.tar.gz"
tar czf "$OUTPUT" -C "$(dirname $OFFLINE_DIR)" "$(basename $OFFLINE_DIR)"

OUTPUT_SZ=$(du -h "$OUTPUT" | awk '{print $1}')
OUTPUT_SHA=$(sha256sum "$OUTPUT" | awk '{print $1}')

echo ""
echo "=== Offline Package Built ==="
echo "  File:    $OUTPUT"
echo "  Size:    $OUTPUT_SZ"
echo "  SHA256:  $OUTPUT_SHA"
echo ""
echo "Transfer to target machine and run:"
echo "  tar xzf $(basename $OUTPUT)"
echo "  cd ${OFFLINE_NAME}"
echo "  sudo ./install-offline.sh"
echo ""
