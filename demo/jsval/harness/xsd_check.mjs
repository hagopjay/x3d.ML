/* XSD parity harness (js-port-of-8dd0d3e): run xsd.js over all 557 corpus bodies and compare with the Python
 * baseline -- canary 8dd0d3e.json (valid + error count) and py-all.json (full error strings + notes).
 * Self-contained: needs only Node 22 and the files in jsval/ (no npm install, no shared shim).
 * Usage: node harness/xsd_check.mjs [--canary <8dd0d3e.json>] [--pyall <py-all.json>] [--json <out.json>] [--quiet]
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const JSVAL = path.resolve(here, '..');
const SCRATCH = '/tmp/claude-0/-home-user/d1db4f4e-b69c-59c1-8b63-a13c27f16e5d/scratchpad';
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const CANARY = opt('--canary', SCRATCH + '/canary/8dd0d3e.json');
const PYALL = opt('--pyall', SCRATCH + '/jsport-notes/py-all.json');
const OUT = opt('--json', null);
const QUIET = args.includes('--quiet');
const REPLAY = '/home/user/x3d.ml/demo/data/replay.json';
const LIVE_DIR = '/home/user/x3d.ml/runs/live-2026-10-17/x3d';

// ---- Node shim for the classic script: self + fs reader + import()
if (typeof globalThis.self === 'undefined') globalThis.self = globalThis;
require(path.join(JSVAL, 'src', '40_xsd.js'));
const X3DVAL = globalThis.X3DVAL;
const xsd = X3DVAL._m.xsd;
const nodeLoadOptions = () => ({
  base: pathToFileURL(JSVAL + path.sep).href,
  read: async (url) => new Uint8Array(fs.readFileSync(url.startsWith('file:') ? fileURLToPath(url) : url)),
  importer: (url) => import(url),
});

// ---- bodies exactly as canary/verdicts.py enumerates them
const bodies = new Map();
for (const it of JSON.parse(fs.readFileSync(REPLAY, 'utf8'))) bodies.set('replay/' + it.k, it.b);
const dec = new TextDecoder('utf-8'); // ~ Python open(errors="replace"); cross-checked against py-all xml below
const liveFiles = [];
for (const model of fs.readdirSync(LIVE_DIR).sort()) {
  const d = path.join(LIVE_DIR, model);
  if (!fs.statSync(d).isDirectory()) continue;
  for (const f of fs.readdirSync(d)) if (f.endsWith('.x3d')) liveFiles.push(path.join(d, f));
}
liveFiles.sort();
for (const f of liveFiles) bodies.set('live/' + f.split('/').slice(-2).join('/'), dec.decode(fs.readFileSync(f)));

const canary = JSON.parse(fs.readFileSync(CANARY, 'utf8')).verdicts;
const pyall = fs.existsSync(PYALL) ? JSON.parse(fs.readFileSync(PYALL, 'utf8')) : null;

// ---- load + compile
const tLoad0 = performance.now();
await xsd.load(nodeLoadOptions());
const loadMs = performance.now() - tLoad0;
const compileMs = {};
for (const v of ['4.0', '4.1']) { xsd.compile(v); compileMs[v] = Math.round(xsd.state.compileMs[v]); }

// ---- run
const rows = [], times = [];
let agreeValid = 0, agreeCount = 0, agreeFull = 0, bodyMismatch = 0, nFull = 0;
for (const [k, xml] of bodies) {
  const py = canary[k];
  if (!py) { rows.push({ key: k, py: 'MISSING IN CANARY', js: '' }); continue; }
  if (pyall && pyall[k] && pyall[k].xml !== xml) bodyMismatch++;
  const t0 = performance.now();
  const r = xsd.validateXml(xml);
  times.push(performance.now() - t0);
  const okValid = r.valid === py.xsd;
  const okCount = r.errors.length === (py.nxsd ?? 0);
  if (okValid) agreeValid++;
  if (okValid && okCount) agreeCount++;
  let okFull = null;
  if (pyall && pyall[k]) {
    nFull++;
    okFull = JSON.stringify(r) === JSON.stringify(pyall[k].validate);
    if (okFull) agreeFull++;
  }
  if (!okValid || !okCount || okFull === false) {
    rows.push({
      key: k,
      py: { xsd: py.xsd, nxsd: py.nxsd, errors: pyall?.[k]?.validate?.errors, notes: pyall?.[k]?.validate?.notes },
      js: { xsd: r.valid, nxsd: r.errors.length, errors: r.errors, notes: r.notes },
    });
  }
}
const sorted = [...times].sort((a, b) => a - b);
const q = (p) => sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
const shippedFiles = ['src/40_xsd.js', 'vendor/libxml2-wasm.bundle.mjs', 'vendor/LICENSE.libxml2-wasm', 'vendor/LICENSE.libxml2', 'vendor/README.md', 'data/nodes-4.0.json', 'data/nodes-4.1.json', ...xsd.SCHEMA_FILES.map((f) => 'data/schemas/' + f)];
const bytes = Object.fromEntries(shippedFiles.map((f) => [f, fs.statSync(path.join(JSVAL, f)).size]));
const summary = {
  label: X3DVAL.label,
  total: bodies.size,
  agree: { valid: agreeValid, valid_and_count: agreeCount, full_dict: pyall ? agreeFull : null, full_total: pyall ? nFull : null, total: bodies.size },
  body_text_mismatch_vs_pyall: bodyMismatch,
  disagreements: rows,
  load_ms: Math.round(loadMs), compile_ms: compileMs,
  median_ms: +q(0.5).toFixed(3), p90_ms: +q(0.9).toFixed(3), max_ms: +sorted[sorted.length - 1].toFixed(1), mean_ms: +(times.reduce((a, b) => a + b, 0) / times.length).toFixed(3),
  bytes_total: Object.values(bytes).reduce((a, b) => a + b, 0), bytes,
};
if (!QUIET) {
  console.log(`bodies ${summary.total}  agree valid ${agreeValid}/${summary.total}  valid+count ${agreeCount}/${summary.total}` + (pyall ? `  full dict ${agreeFull}/${nFull}` : '') + `  body-text mismatches vs py-all ${bodyMismatch}`);
  console.log(`load ${summary.load_ms} ms  compile 4.0 ${compileMs['4.0']} ms  4.1 ${compileMs['4.1']} ms  validate median ${summary.median_ms} ms  p90 ${summary.p90_ms} ms  max ${summary.max_ms} ms (first call)  shipped ${summary.bytes_total} B`);
  if (rows.length) {
    console.log('\nDISAGREEMENTS (key | python | js):');
    for (const r of rows) console.log(`- ${r.key}\n    py: ${JSON.stringify(r.py)}\n    js: ${JSON.stringify(r.js)}`);
  } else console.log('no disagreements');
}
if (OUT) fs.writeFileSync(OUT, JSON.stringify(summary, null, 1));
process.exitCode = rows.length ? 1 : 0;
