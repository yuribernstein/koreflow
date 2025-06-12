#!/bin/bash

set -e

APP_NAME="korectl"
ENTRY_POINT="korectl.py"
BUILD_DIR="build"

echo "🧹 [1/5] Cleaning previous build..."
rm -rf "$BUILD_DIR"/*
mkdir -p "$BUILD_DIR"

source ./korectl/bin/activate
echo "[2/5] Building $APP_NAME binary..."

python3 -m nuitka \
  --standalone \
  --onefile \
  --follow-imports \
  --output-dir="$BUILD_DIR" \
  --output-filename="$APP_NAME" \
  --include-data-files=dsl.schema.json=dsl.schema.json \
  --include-data-files=module.schema.json=module.schema.json \
  "$ENTRY_POINT"

echo "[3/5] Build complete!"
echo "Structure:"
tree "$BUILD_DIR" || ls -R "$BUILD_DIR"

echo "To run: cd $BUILD_DIR && ./$APP_NAME"

echo "[4/5] Cleaning up temp build artifacts..."
rm -rf "$BUILD_DIR/korectl.build" "$BUILD_DIR/korectl.dist" "$BUILD_DIR/korectl.onefile-build"

