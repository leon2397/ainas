#!/bin/bash
# AIqizhi DEB Package Builder
# Usage: ./build-deb.sh [--arch arm64|amd64] [--version X.Y.Z]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$BUILD_DIR")"
ARCH="arm64"
VERSION="2.0.0"

while [[ $# -gt 0 ]]; do
    case $1 in
        --arch)   ARCH="$2"; shift 2 ;;
        --version) VERSION="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--arch arm64|amd64] [--version X.Y.Z]"
            exit 0 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

if [ "$ARCH" = "auto" ]; then
    MACHINE=$(uname -m)
    case $MACHINE in
        aarch64|arm64) ARCH="arm64" ;;
        x86_64|amd64)  ARCH="amd64" ;;
        *) echo "Unsupported arch: $MACHINE"; exit 1 ;;
    esac
fi

PKG_NAME="aiqizhi_${VERSION}_${ARCH}"
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

echo "=== Building DEB: $PKG_NAME ==="
echo "  Arch:    $ARCH"
echo "  Version: $VERSION"
echo "  Project: $PROJECT_DIR"
echo ""

# 1. Copy project files
echo "[1/5] Copying project files..."
mkdir -p "$TMP_DIR/$PKG_NAME/opt/aiqizhi"
cp -r "$PROJECT_DIR/backend" "$TMP_DIR/$PKG_NAME/opt/aiqizhi/"
cp -r "$PROJECT_DIR/frontend" "$TMP_DIR/$PKG_NAME/opt/aiqizhi/"
cp -r "$PROJECT_DIR/config" "$TMP_DIR/$PKG_NAME/opt/aiqizhi/"
cp -r "$PROJECT_DIR/arm" "$TMP_DIR/$PKG_NAME/opt/aiqizhi/"

# Remove venv, __pycache__, test files
find "$TMP_DIR/$PKG_NAME/opt/aiqizhi" -type d -name "venv" -exec rm -rf {} + 2>/dev/null || true
find "$TMP_DIR/$PKG_NAME/opt/aiqizhi" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$TMP_DIR/$PKG_NAME/opt/aiqizhi" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# 2. Copy systemd and config files
echo "[2/5] Copying systemd files..."
mkdir -p "$TMP_DIR/$PKG_NAME/etc/systemd/system"
cp "$BUILD_DIR/templates/aiqizhi.service" "$TMP_DIR/$PKG_NAME/etc/systemd/system/"
mkdir -p "$TMP_DIR/$PKG_NAME/etc/logrotate.d"
cp "$BUILD_DIR/templates/aiqizhi.logrotate" "$TMP_DIR/$PKG_NAME/etc/logrotate.d/aiqizhi"
mkdir -p "$TMP_DIR/$PKG_NAME/etc/aiqizhi"
cp "$BUILD_DIR/templates/aiqizhi.conf" "$TMP_DIR/$PKG_NAME/etc/aiqizhi/"

# 3. Create empty data dirs
echo "[3/5] Creating data directories..."
mkdir -p "$TMP_DIR/$PKG_NAME/var/lib/aiqizhi/media"
mkdir -p "$TMP_DIR/$PKG_NAME/var/lib/aiqizhi/thumbnails"
mkdir -p "$TMP_DIR/$PKG_NAME/var/lib/aiqizhi/database"
mkdir -p "$TMP_DIR/$PKG_NAME/var/log/aiqizhi"

# 4. Copy DEBIAN control files
echo "[4/5] Preparing DEBIAN control..."
cp "$BUILD_DIR/packages/deb/DEBIAN/control" "$TMP_DIR/$PKG_NAME/DEBIAN/"
cp "$BUILD_DIR/packages/deb/DEBIAN/preinst" "$TMP_DIR/$PKG_NAME/DEBIAN/"
cp "$BUILD_DIR/packages/deb/DEBIAN/postinst" "$TMP_DIR/$PKG_NAME/DEBIAN/"
cp "$BUILD_DIR/packages/deb/DEBIAN/prerm" "$TMP_DIR/$PKG_NAME/DEBIAN/"
cp "$BUILD_DIR/packages/deb/DEBIAN/postrm" "$TMP_DIR/$PKG_NAME/DEBIAN/"

# Replace placeholders
PKG_SIZE=$(du -sk "$TMP_DIR/$PKG_NAME" | awk '{print $1}')
sed -i "s/@ARCH@/$ARCH/g" "$TMP_DIR/$PKG_NAME/DEBIAN/control"
sed -i "s/@SIZE@/$PKG_SIZE/g" "$TMP_DIR/$PKG_NAME/DEBIAN/control"

# Set DEBIAN script permissions
chmod 0755 "$TMP_DIR/$PKG_NAME/DEBIAN/preinst"
chmod 0755 "$TMP_DIR/$PKG_NAME/DEBIAN/postinst"
chmod 0755 "$TMP_DIR/$PKG_NAME/DEBIAN/prerm"
chmod 0755 "$TMP_DIR/$PKG_NAME/DEBIAN/postrm"

# 5. Build package
echo "[5/5] Building .deb package..."
OUTPUT_DIR="$BUILD_DIR/packages"
mkdir -p "$OUTPUT_DIR"
dpkg-deb --build --root-owner-group "$TMP_DIR/$PKG_NAME" "$OUTPUT_DIR/"

# Show result
PKG_FILE="$OUTPUT_DIR/${PKG_NAME}.deb"
PKG_SZ=$(du -h "$PKG_FILE" | awk '{print $1}')
PKG_SHA=$(sha256sum "$PKG_FILE" | awk '{print $1}')

echo ""
echo "=== Build Complete ==="
echo "  Package: $PKG_FILE"
echo "  Size:    $PKG_SZ"
echo "  SHA256:  $PKG_SHA"
echo ""
echo "Install: dpkg -i $PKG_FILE"
