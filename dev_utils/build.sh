#!/bin/bash

set -e

APP_NAME="koreflow"
ENTRY_POINT="koreflow.py"

if [ -z $1 ]; then
  BUILD_DIR="./build"
else
  BUILD_DIR=$1
fi

python3 -m venv _venv_
source _venv_/bin/activate

pip3 install --upgrade pip
pip3 install -r ../requirements.txt

echo "🧹 [1/5] Cleaning previous build..."
mkdir -p "$BUILD_DIR"
rm -rf "$BUILD_DIR"/*


echo "⚙️ [2/5] Building $APP_NAME binary with Nuitka..."

python3 -m nuitka \
  --standalone \
  --onefile \
  --follow-imports \
  --output-dir="$BUILD_DIR" \
  --output-filename="$APP_NAME" \
  --enable-plugin=pylint-warnings \
  --nofollow-import-to=workflows \
  --nofollow-import-to=logs \
  --nofollow-import-to=repos \
  --nofollow-import-to=configuration \
  --include-data-dir=engine=./engine \
  --include-data-dir=commons=./commons \
  --include-module=smtplib \
  "$ENTRY_POINT"

echo "📦 [3/5] Copying runtime folders next to the binary..."

cp -r workflows "$BUILD_DIR/"
cp -r modules "$BUILD_DIR/"
mkdir -p "$BUILD_DIR/logs"
mkdir -p "$BUILD_DIR/lifetimes/completed"

echo "✅ [4/5] Build complete!"
echo "Structure:"
tree "$BUILD_DIR" || ls -R "$BUILD_DIR"

echo "🚀 To run: cd $BUILD_DIR && ./$APP_NAME"

echo "🧽 [5/5] Cleaning up Nuitka temp build artifacts..."
rm -rf $BUILD_DIR/web.build $BUILD_DIR/web.dist $BUILD_DIR/web.onefile-build