#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="$PROJECT_ROOT/.venv-macos"
DIST_DIR="$PROJECT_ROOT/dist/macos"
WORK_DIR="$PROJECT_ROOT/build/macos"
ARCH="$(uname -m)"
ZIP_FILE="$PROJECT_ROOT/dist/DataViewer-macOS-$ARCH.zip"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$PROJECT_ROOT/requirements.txt"

rm -rf "$DIST_DIR" "$WORK_DIR"
"$VENV_DIR/bin/python" -m PyInstaller \
    --noconfirm \
    --clean \
    --distpath "$DIST_DIR" \
    --workpath "$WORK_DIR" \
    "$PROJECT_ROOT/client/RealDataViewClient.spec"

ditto -c -k --sequesterRsrc --keepParent \
    "$DIST_DIR/DataViewer.app" \
    "$ZIP_FILE"

echo "Build completed:"
echo "  APP: $DIST_DIR/DataViewer.app"
echo "  ZIP: $ZIP_FILE"
