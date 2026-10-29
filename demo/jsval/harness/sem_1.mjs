/* Parity harness for semantic group B (js-port-of-8dd0d3e): field / ROUTE typing.
 * Runs ONLY the group-B checks (src/51_checksB.js) over the 557 corpus bodies and the
 * probe scenes, and compares against the Python fork (commit 8dd0d3e):
 *   - corpus: Python validate_semantic reports cached in <scratch>/jsport-node/py_reports.json
 *     (created by jsport-node/py_reports.py through python3 -I if missing)
 *   - probes: harness/py-dump.py run live through python3 -I on the probes directory
 * Comparison per body, restricted to group-B check ids:
 *   1. multiset of (section, id)                                        -> "agree"
 *   2. ordered sequence of (section, id, full message) over the whole body -> "exact"
 * Usage: node harness/sem_1.mjs [--json out.json] [--verbose]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const shim = require('./node-shim.cjs');

const SCRATCH = '/tmp/claude-0/-home-user/d1db4f4e-b69c-59c1-8b63-a13c27f16e5d/scratchpad';
const FORK = SCRATCH + '/fork-main';
const PY_REPORTS = SCRATCH + '/jsport-node/py_reports.json';
const PY_REPORTS_SCRIPT = SCRATCH + '/jsport-node/py_reports.py';
const PROBES_DIR = path.join(here, 'probes', 'B field-route-typing (src',
  '51_checksB.js): check_containerfield, check_route_validity, check_dead_boolean_routes (+ exports X3DVAL._m.routeHelpers: scriptFields, protoInterfaces, endpointFields, resolveRouteField, fieldAccepts, nodeFieldMap',
  'typeAncestry wrappers)');
const PROBES_PY = SCRATCH + '/jsport-node/py_probes_B.json';

const args = process.argv.slice(2);
const verbose = args.includes('--verbose');
const jsonOut = args.includes('--json') ? args[args.indexOf('--json') + 1] : null;

// ---- library
const X3DVAL = await shim.ready({ files: ['00_ns', '10_py', '20_parse', '30_uom', '51_checksB'] });
const { t, py, uom, checks, checksB } = X3DVAL._m;
const MY_IDS = new Set(checksB.ids);
const LEVEL_OF = { Errors: 'error', Warnings: 'warning', Info: 'info' };

function runB(xml) {
  let root;
  try { root = t.parseSnapshot(xml, t.SEM_OPTS); } catch (e) { return { status: 'parse-error', detail: t.parseErrorString(e), diags: [] }; }
  const scene = t.findScene(root);
  if (!scene) return { status: 'no-scene', diags: [] };
  const diags = [];
  const ctx = { root, scene, version: t.get(root, 'version', ''), uom, py, t, emit: (level, check, message) => diags.push({ level, check, message }) };
  for (const fn of checksB.functions) checks[fn](ctx);
  return { status: 'report', diags };
}

// Parse a Python markdown report into [{level, check, message}], keeping order. A message may span
// several lines when an attribute value contains newlines: continuation lines (anything that is not
// a new item, a section header or the blank separator before a header) are re-attached.
function parsePy(report) {
  const out = [];
  const lines = report.split('\n');
  let level = null;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const m = /^## (Errors|Warnings|Info)$/.exec(line);
    if (m) { level = LEVEL_OF[m[1]]; continue; }
    if (!level) continue;
    if (line.startsWith('- **[')) {
      const close = line.indexOf(']** ');
      if (close < 0) continue;
      out.push({ level, check: line.slice(5, close), message: line.slice(close + 4) });
    } else if (out.length && !(line === '' && (i + 1 >= lines.length || lines[i + 1] === '' || lines[i + 1].startsWith('## ') || /^## /.test(lines[i - 1])))) {
      out[out.length - 1].message += '\n' + line;
    }
  }
  return out;
}
const key2 = d => d.level + ' ' + d.check;
const key3 = d => d.level + ' ' + d.check + ' ' + d.message;
const sortedJoin = arr => arr.slice().sort().join('\u0001');

function compare(pyDiags, jsDiags) {
  const pyB = pyDiags.filter(d => MY_IDS.has(d.check));
  const agree = sortedJoin(pyB.map(key2)) === sortedJoin(jsDiags.map(key2));
  const exact = pyB.map(key3).join('\u0002') === jsDiags.map(key3).join('\u0002');
  return { agree, exact, pyB };
}
function diffDetail(pyB, jsDiags) {
  const p = pyB.map(key3), j = jsDiags.map(key3);
  const pc = new Map(), jc = new Map();
  for (const x of p) pc.set(x, (pc.get(x) || 0) + 1);
  for (const x of j) jc.set(x, (jc.get(x) || 0) + 1);
  const onlyPy = [], onlyJs = [];
  for (const [x, n] of pc) if ((jc.get(x) || 0) < n) onlyPy.push(x);
  for (const [x, n] of jc) if ((pc.get(x) || 0) < n) onlyJs.push(x);
  if (!onlyPy.length && !onlyJs.length && p.join('\u0002') !== j.join('\u0002')) return { onlyPy: ['ORDER: ' + p.join(' | ')], onlyJs: ['ORDER: ' + j.join(' | ')] };
  return { onlyPy, onlyJs };
}

// ---- corpus bodies
const bodies = new Map();
for (const it of JSON.parse(fs.readFileSync('/home/user/x3d.ml/demo/data/replay.json', 'utf8'))) bodies.set('replay/' + it.k, it.b);
const liveRoot = '/home/user/x3d.ml/runs/live-2026-10-17/x3d';
const dec = new TextDecoder('utf-8');   // errors="replace" like Python
const liveFiles = [];
for (const model of fs.readdirSync(liveRoot)) for (const f of fs.readdirSync(path.join(liveRoot, model))) if (f.endsWith('.x3d')) liveFiles.push(path.join(liveRoot, model, f));
liveFiles.sort();
for (const f of liveFiles) bodies.set('live/' + f.split('/').slice(-2).join('/'), dec.decode(fs.readFileSync(f)));

if (!fs.existsSync(PY_REPORTS)) {
  execFileSync('python3', ['-I', PY_REPORTS_SCRIPT, PY_REPORTS], { cwd: SCRATCH + '/canary', stdio: 'inherit' });
}
const pyReports = JSON.parse(fs.readFileSync(PY_REPORTS, 'utf8'));

const result = { label: X3DVAL.label, checks: checksB.ids, agree: { bodies: 0, total: 0, exact: 0, probes: 0, probes_total: 0, probes_exact: 0 }, disagreements: [], inexact: [], ms: { total: 0, max: 0 }, id_counts: { py: {}, js: {} } };
const statusCounts = { report: 0, 'parse-error': 0, 'no-scene': 0 };
const bump = (o, k) => { o[k] = (o[k] || 0) + 1; };
for (const [k, xml] of bodies) {
  result.agree.total++;
  const t0 = performance.now();
  const r = runB(xml);
  const ms = performance.now() - t0;
  result.ms.total += ms; if (ms > result.ms.max) result.ms.max = ms;
  statusCounts[r.status]++;
  const rep = pyReports[k];
  if (rep === undefined) { result.disagreements.push({ key: k, check: '*', py: 'MISSING', js: r.status }); continue; }
  const pyD = parsePy(rep);
  if (r.status !== 'report' && !rep.startsWith('# Semantic Check: ' + (r.status === 'parse-error' ? 'Parse Error' : 'No Scene'))) {
    result.disagreements.push({ key: k, check: '*', py: rep.split('\n')[0], js: r.status });
    continue;
  }
  const c = compare(pyD, r.diags);
  for (const d of c.pyB) bump(result.id_counts.py, d.check);
  for (const d of r.diags) bump(result.id_counts.js, d.check);
  if (c.agree) result.agree.bodies++;
  if (c.exact) result.agree.exact++;
  if (!c.agree || !c.exact) {
    const d = diffDetail(c.pyB, r.diags);
    const entry = { key: k, check: [...new Set([...d.onlyPy, ...d.onlyJs].map(x => x.split(' ')[1]))].join(','), py: d.onlyPy, js: d.onlyJs };
    if (!c.agree) result.disagreements.push(entry); else result.inexact.push(entry);
  }
}
result.status_counts = statusCounts;

// ---- probes
if (fs.existsSync(PROBES_DIR)) {
  const probeFiles = fs.readdirSync(PROBES_DIR).filter(f => f.endsWith('.x3d')).sort();
  if (probeFiles.length) {
    execFileSync('python3', ['-I', path.join(here, 'py-dump.py'), FORK, PROBES_PY, PROBES_DIR], { cwd: SCRATCH + '/canary', stdio: ['ignore', 'ignore', 'inherit'] });
    const pyProbes = JSON.parse(fs.readFileSync(PROBES_PY, 'utf8'));
    const dirKey = path.basename(PROBES_DIR);
    result.probes = [];
    for (const f of probeFiles) {
      result.agree.probes_total++;
      const xml = fs.readFileSync(path.join(PROBES_DIR, f), 'utf8');
      const r = runB(xml);
      const rep = pyProbes[dirKey + '/' + f].semantic;
      const pyD = parsePy(rep);
      const okStatus = r.status === 'report' ? !rep.startsWith('# Semantic Check: Parse Error') && !rep.startsWith('# Semantic Check: No Scene')
        : rep.startsWith('# Semantic Check: ' + (r.status === 'parse-error' ? 'Parse Error' : 'No Scene'));
      const c = compare(pyD, r.diags);
      const agree = okStatus && c.agree, exact = okStatus && c.exact;
      if (agree) result.agree.probes++;
      if (exact) result.agree.probes_exact++;
      const row = { probe: f, status: r.status, agree, exact, n_py: c.pyB.length, n_js: r.diags.length, ids_py: c.pyB.map(d => d.check), ids_js: r.diags.map(d => d.check) };
      if (!exact) { const d = diffDetail(c.pyB, r.diags); row.py = d.onlyPy; row.js = d.onlyJs; row.py_report = rep; row.js_diags = r.diags; result.disagreements.push({ key: 'probe/' + f, check: [...new Set([...d.onlyPy, ...d.onlyJs].map(x => x.split(' ')[1]))].join(','), py: d.onlyPy, js: d.onlyJs }); }
      if (verbose) { row.js_diags = r.diags; row.py_report = rep; }
      result.probes.push(row);
    }
  }
}

result.ms.avg = result.ms.total / Math.max(1, result.agree.total);
if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(result, null, 1));
const summary = { agree: result.agree, status_counts: statusCounts, id_counts: result.id_counts, ms_avg: +result.ms.avg.toFixed(3), ms_max: +result.ms.max.toFixed(1), disagreements: result.disagreements.length, inexact: result.inexact.length };
console.log(JSON.stringify(summary));
if (verbose || result.disagreements.length || result.inexact.length) {
  for (const d of result.disagreements.slice(0, 40)) console.log('DISAGREE', JSON.stringify(d));
  for (const d of result.inexact.slice(0, 40)) console.log('INEXACT', JSON.stringify(d));
}
if (verbose && result.probes) for (const p of result.probes) console.log('PROBE', JSON.stringify({ probe: p.probe, ids_py: p.ids_py, ids_js: p.ids_js }));
process.exitCode = result.disagreements.length ? 1 : 0;
