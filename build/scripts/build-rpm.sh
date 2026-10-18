#!/bin/bash
# AIqizhi RPM Package Builder
# Usage: ./build-rpm.sh [--arch aarch64|x86_64] [--version X.Y.Z]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$BUILD_DIR")"
ARCH="aarch64"
VERSION="2.0.0"
RELEASE="1"

while [[ $# -gt 0 ]]; do
    case $1 in
        --arch)    ARCH="$2"; shift 2 ;;
        --version) VERSION="$2"; shift 2 ;;
        --release) RELEASE="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--arch aarch64|x86_64] [--version X.Y.Z]"
            exit 0 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

if [ "$ARCH" = "auto" ]; then
    ARCH=$(uname -m)
fi

echo "=== Building RPM: aiqizhi-${VERSION}-${RELEASE}.${ARCH} ==="
echo "  Arch:    $ARCH"
echo "  Version: $VERSION"
echo "  Release: $RELEASE"
echo ""

# Setup rpmbuild tree
RPMBUILD_ROOT="${HOME}/rpmbuild"
for d in SOURCES SPECS RPMS SRPMS BUILD; do
    mkdir -p "$RPMBUILD_ROOT/$d"
done

# Create source tarball
TARBALL="aiqizhi-${VERSION}.tar.gz"
echo "[1/3] Creating source tarball..."
TMP_SRC=$(mktemp -d)
cp -r "$PROJECT_DIR/backend" "$TMP_SRC/aiqizhi-${VERSION}/"
cp -r "$PROJECT_DIR/frontend" "$TMP_SRC/aiqizhi-${VERSION}/"
cp -r "$PROJECT_DIR/config" "$TMP_SRC/aiqizhi-${VERSION}/"
cp -r "$PROJECT_DIR/arm" "$TMP_SRC/aiqizhi-${VERSION}/"
cp -r "$BUILD_DIR/templates" "$TMP_SRC/aiqizhi-${VERSION}/packaging/"

# Cleanup
find "$TMP_SRC" -type d -name "venv" -exec rm -rf {} + 2>/dev/null || true
find "$TMP_SRC" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

tar czf "$RPMBUILD_ROOT/SOURCES/$TARBALL" -C "$TMP_SRC" "aiqizhi-${VERSION}"
rm -rf "$TMP_SRC"

# Prepare spec file
echo "[2/3] Preparing spec file..."
sed -e "s/@VERSION@/$VERSION/g"     -e "s/@RELEASE@/$RELEASE/g"     -e "s/@ARCH@/$ARCH/g"     "$BUILD_DIR/packages/rpm/SPECS/aiqizhi.spec"     > "$RPMBUILD_ROOT/SPECS/aiqizhi.spec"

# Build RPM
echo "[3/3] Building RPM..."
rpmbuild -bb     --define "_topdir $RPMBUILD_ROOT"     --target "$ARCH"     "$RPMBUILD_ROOT/SPECS/aiqizhi.spec"

# Copy result
OUTPUT_DIR="$BUILD_DIR/packages"
mkdir -p "$OUTPUT_DIR"
cp "$RPMBUILD_ROOT/RPMS/$ARCH/aiqizhi-${VERSION}-${RELEASE}.${ARCH}.rpm" "$OUTPUT_DIR/" 2>/dev/null ||     cp "$RPMBUILD_ROOT/RPMS/${ARCH}/aiqizhi-${VERSION}-${RELEASE}.${ARCH}.rpm" "$OUTPUT_DIR/" 2>/dev/null || true

# Show result
PKG_FILE="$OUTPUT_DIR/aiqizhi-${VERSION}-${RELEASE}.${ARCH}.rpm"
if [ -f "$PKG_FILE" ]; then
    PKG_SZ=$(du -h "$PKG_FILE" | awk '{print $1}')
    PKG_SHA=$(sha256sum "$PKG_FILE" | awk '{print $1}')
    echo ""
    echo "=== Build Complete ==="
    echo "  Package: $PKG_FILE"
    echo "  Size:    $PKG_SZ"
    echo "  SHA256:  $PKG_SHA"
    echo ""
    echo "Install: rpm -ivh $PKG_FILE"
else
    echo ""
    echo "RPM file not found in expected location."
    echo "Check $RPMBUILD_ROOT/RPMS/ for output."
fi
