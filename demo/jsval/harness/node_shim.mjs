/* Node 22 ESM shim for the shipped classic script x3dval.js (js-port-of-8dd0d3e).
 *
 *   import { X3DVAL, load } from './node_shim.mjs';
 *   await load();                       // = X3DVAL.load({base: file URL of jsval/, read: fs, importer: import()})
 *   X3DVAL.validate(xml, {version})
 *
 * x3dval.js is evaluated through require() (its CommonJS wrapper is harmless: the script only
 * writes to self.X3DVAL). globalThis.self is set so the browser-style globals resolve.
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
globalThis.self = globalThis;

const require = createRequire(import.meta.url);
require(path.join(ROOT, 'x3dval.js'));
export const X3DVAL = globalThis.X3DVAL;

function toPath(u) {
  const s = String(u);
  if (s.startsWith('file:')) return fileURLToPath(s);
  return path.isAbsolute(s) ? s : path.join(ROOT, s);
}
export async function readBytes(u) { return new Uint8Array(fs.readFileSync(toPath(u))); }
export async function importer(u) { return import(/^file:/.test(String(u)) ? String(u) : pathToFileURL(toPath(u)).href); }
export function nodeLoadOptions(extra) {
  return Object.assign({ base: pathToFileURL(ROOT + path.sep).href, read: readBytes, importer }, extra || {});
}
export function load(extra) { return X3DVAL.load(nodeLoadOptions(extra)); }
