/* Node 22 shim for the classic-script library (js-port-of-8dd0d3e).
 * Shared by every harness; two entry styles are supported:
 *
 *   // XSD module style (harness/xsd_check.mjs):
 *   const { loadScripts, nodeLoadOptions } = require('./node-shim.cjs');
 *   const X3DVAL = loadScripts(['xsd.js']);            // names relative to jsval/ or jsval/src/
 *   await X3DVAL._m.xsd.load(nodeLoadOptions());       // {base, read, importer} backed by fs + import()
 *
 *   // semantic-check style (harness/sem_*.mjs):
 *   const shim = require('./node-shim.cjs');
 *   const X3DVAL = await shim.ready({ files: ['00_ns','10_py','20_parse','30_uom','50_checksA'] });
 *   // -> libxml2-wasm injected via X3DVAL._m.t.setLib and shared in X3DVAL._m.libxml2.lib,
 *   //    data/uom-4.1.json + nodes-4.x.json fed to X3DVAL._m.uom.setData
 *
 * With no `files`, ready() loads x3dval.js when it exists, else every src/*.js in name order.
 * Loading is idempotent.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { pathToFileURL, fileURLToPath } = require('url');

const ROOT = path.resolve(__dirname, '..');
globalThis.self = globalThis;

const loadedFiles = new Set();
function resolveScript(name) {
  const cands = [path.join(ROOT, name), path.join(ROOT, 'src', name), path.join(ROOT, 'src', name + '.js'), path.join(ROOT, name + '.js')];
  for (const c of cands) if (fs.existsSync(c) && fs.statSync(c).isFile()) return c;
  throw new Error('node-shim: script not found: ' + name);
}
function loadScripts(names) {
  const list = names.map(resolveScript);
  for (const f of list) {
    if (loadedFiles.has(f)) continue;
    loadedFiles.add(f);
    require(f);                      // classic script: the CJS wrapper is harmless, it writes to self.X3DVAL
  }
  return globalThis.X3DVAL;
}
function loadSources(files) {
  if (files && files.length) return loadScripts(files);
  if (fs.existsSync(path.join(ROOT, 'x3dval.js'))) return loadScripts(['x3dval.js']);
  return loadScripts(fs.readdirSync(path.join(ROOT, 'src')).filter(f => /\.js$/.test(f)).sort());
}

function toPath(u) {
  const s = String(u);
  if (s.startsWith('file:')) return fileURLToPath(s);
  return path.isAbsolute(s) ? s : path.join(ROOT, s);
}
async function readBytes(u) { return new Uint8Array(fs.readFileSync(toPath(u))); }
async function importer(u) { return import(/^file:/.test(String(u)) ? String(u) : pathToFileURL(toPath(u)).href); }
function nodeLoadOptions(extra) {
  return Object.assign({ base: pathToFileURL(ROOT + path.sep).href, read: readBytes, importer }, extra || {});
}

let libPromise = null;
function loadLib() {
  const X3DVAL = globalThis.X3DVAL;
  const shared = X3DVAL && X3DVAL._m && (X3DVAL._m.libxml2 || (X3DVAL._m.libxml2 = { promise: null, lib: null, url: null }));
  if (shared && shared.promise) return shared.promise;
  if (!libPromise) {
    const url = pathToFileURL(path.join(ROOT, 'vendor', 'libxml2-wasm.bundle.mjs')).href;
    libPromise = import(url).then(lib => { if (shared) { shared.lib = lib; shared.url = url; } return lib; });
    if (shared) shared.promise = libPromise;
  }
  return libPromise;
}

function readJson(rel) {
  const p = path.join(ROOT, rel);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null;
}

async function ready(opts) {
  opts = opts || {};
  const X3DVAL = loadSources(opts.files);
  if (X3DVAL._m.t && !X3DVAL._m.t.lib()) X3DVAL._m.t.setLib(await loadLib());
  if (X3DVAL._m.uom && !X3DVAL._m.uom.nodes) {
    X3DVAL._m.uom.setData(readJson('data/uom-4.1.json'), readJson('data/nodes-4.0.json'), readJson('data/nodes-4.1.json'));
  }
  return X3DVAL;
}

module.exports = { ROOT, loadScripts, loadSources, nodeLoadOptions, readBytes, importer, loadLib, readJson, ready };
