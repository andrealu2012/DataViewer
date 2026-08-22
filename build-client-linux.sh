#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This build must run on Linux (Ubuntu 22.04 or newer is recommended)." >&2
    exit 1
fi

for command_name in dpkg dpkg-deb install ln; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Missing required command: $command_name" >&2
        exit 1
    fi
done

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv-linux}"
VERSION="${VERSION:-1.0.0}"
DEB_ARCH="${DEB_ARCH:-$(dpkg --print-architecture)}"
PACKAGE_NAME="dataviewer"
DIST_DIR="$PROJECT_ROOT/dist/linux"
WORK_DIR="$PROJECT_ROOT/build/linux"
PACKAGE_ROOT="$PROJECT_ROOT/build/deb/${PACKAGE_NAME}_${VERSION}_${DEB_ARCH}"
DEB_FILE="$PROJECT_ROOT/dist/DataViewer_${VERSION}_${DEB_ARCH}.deb"

if [[ ! "$VERSION" =~ ^[0-9][0-9A-Za-z.+:~-]*$ ]]; then
    echo "Invalid Debian package version: $VERSION" >&2
    exit 1
fi

if [[ ! "$DEB_ARCH" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
    echo "Invalid Debian package architecture: $DEB_ARCH" >&2
    exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$PROJECT_ROOT/requirements.txt"

rm -rf "$DIST_DIR" "$WORK_DIR" "$PACKAGE_ROOT"
mkdir -p "$DIST_DIR" "$WORK_DIR" "$PACKAGE_ROOT/DEBIAN"

"$VENV_DIR/bin/python" -m PyInstaller \
    --noconfirm \
    --clean \
    --distpath "$DIST_DIR" \
    --workpath "$WORK_DIR" \
    "$PROJECT_ROOT/client/RealDataViewClient.spec"

install -Dm755 \
    "$DIST_DIR/DataViewer" \
    "$PACKAGE_ROOT/opt/dataviewer/DataViewer"
install -Dm644 \
    "$PROJECT_ROOT/client/icons/tray.png" \
    "$PACKAGE_ROOT/usr/share/icons/hicolor/48x48/apps/dataviewer.png"
install -Dm644 \
    "$PROJECT_ROOT/packaging/linux/dataviewer.desktop" \
    "$PACKAGE_ROOT/usr/share/applications/dataviewer.desktop"
mkdir -p "$PACKAGE_ROOT/usr/bin"
ln -s /opt/dataviewer/DataViewer "$PACKAGE_ROOT/usr/bin/dataviewer"

INSTALLED_SIZE="$(du -sk "$PACKAGE_ROOT/opt" "$PACKAGE_ROOT/usr" | awk '{total += $1} END {print total}')"
printf '%s\n' \
    "Package: $PACKAGE_NAME" \
    "Version: $VERSION" \
    "Section: utils" \
    "Priority: optional" \
    "Architecture: $DEB_ARCH" \
    "Maintainer: DataViewer Contributors <noreply@github.com>" \
    "Homepage: https://github.com/andrealu2012/DataViewer" \
    "Installed-Size: $INSTALLED_SIZE" \
    "Depends: libc6, libdbus-1-3, libegl1, libfontconfig1, libfreetype6, libgl1, libglib2.0-0, libx11-6, libx11-xcb1, libxcb1, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render0, libxcb-render-util0, libxcb-shape0, libxcb-shm0, libxcb-sync1, libxcb-util1, libxcb-xfixes0, libxcb-xinerama0, libxcb-xkb1, libxext6, libxi6, libxkbcommon0, libxkbcommon-x11-0, libxrender1, libxtst6" \
    "Description: Desktop stock quote overlay" \
    " DataViewer displays selected Chinese stock prices and changes in a compact" \
    " desktop overlay with tray controls and configurable display modes." \
    > "$PACKAGE_ROOT/DEBIAN/control"

rm -f "$DEB_FILE"
dpkg-deb --build --root-owner-group "$PACKAGE_ROOT" "$DEB_FILE"

echo "Build completed:"
echo "  Binary: $DIST_DIR/DataViewer"
echo "  DEB:    $DEB_FILE"
