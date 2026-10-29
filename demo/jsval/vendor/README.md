# vendor/ -- libxml2-wasm 0.7.2 (MIT) with its embedded libxml2 WebAssembly build

`libxml2-wasm.bundle.mjs` (1,205,491 bytes, sha256 acde0e047e7fa1e72a6732fd4d12b5607047f4427d83eed3e1dc8e6775e6fc0a)
is a single-file ES-module bundle of the npm package `libxml2-wasm@0.7.2` (https://github.com/jameslan/libxml2-wasm).
The wasm binary is embedded by the package itself (lib/libxml2raw.mjs); there is no separate .wasm file.

Built once with (see ../tools/build-vendor.sh; reproducible, byte-identical):

    echo "export * from 'libxml2-wasm';" > entry.mjs
    npm i libxml2-wasm@0.7.2 esbuild@0.25.12
    npx esbuild entry.mjs --bundle --format=esm --platform=browser --target=es2022 --charset=utf8 --outfile=libxml2-wasm.bundle.mjs

It must stay an ES module (the package uses top-level await, so an IIFE build is impossible); classic scripts load it
with dynamic `import(base + 'vendor/libxml2-wasm.bundle.mjs')`, which works from a page, a classic Worker and a blob:
Worker under `script-src 'self' 'wasm-unsafe-eval'`. The bundle contains no eval / new Function; instantiation uses
WebAssembly.instantiate. One guarded `import("node:module")` runs only under Node.

Licenses: LICENSE.libxml2-wasm (wrapper, MIT), LICENSE.libxml2 (libxml2, MIT-style).
