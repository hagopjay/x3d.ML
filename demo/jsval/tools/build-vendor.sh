#!/bin/sh
# One-time (documented, not required at runtime) build of vendor/libxml2-wasm.bundle.mjs.
# Runs in a scratch npm directory, never inside the repo. Usage: tools/build-vendor.sh <scratch-dir>
set -e
SCRATCH="${1:?scratch dir}"; HERE="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$SCRATCH" && cd "$SCRATCH"
[ -f package.json ] || npm init -y >/dev/null
npm i libxml2-wasm@0.7.2 esbuild@0.25.12
echo "export * from 'libxml2-wasm';" > entry.mjs
npx esbuild entry.mjs --bundle --format=esm --platform=browser --target=es2022 --charset=utf8 --outfile="$HERE/vendor/libxml2-wasm.bundle.mjs"
cp node_modules/libxml2-wasm/LICENSE "$HERE/vendor/LICENSE.libxml2-wasm"
cp node_modules/libxml2-wasm/LICENSE.libxml2 "$HERE/vendor/LICENSE.libxml2"
sha256sum "$HERE/vendor/libxml2-wasm.bundle.mjs"
