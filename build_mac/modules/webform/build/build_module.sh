#!/bin/bash
#build_module.sh

# This script builds the Seyoawe webform module using esbuild.
# user it to modify the webform

# Go to script directory (build/)
cd "$(dirname "$0")"
rm -rf ./dist/*

# Run the build
echo "🔧 Building module in: $(pwd)/.."
npx esbuild --version >/dev/null 2>&1 || { echo "❌ esbuild is not installed. Run 'npm install --save-dev esbuild'"; exit 1; }

node build.js
mkdir -p dist/configs
cp ../configs/*.js dist/configs/
cp ../custom.css ./dist/custom.css
mkdir -p ./dist/icons
cp -r ../assets/icons/* ./dist/icons/
