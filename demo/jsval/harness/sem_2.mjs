/* Parity harness for semantic group C (js-port-of-8dd0d3e).
 * Runs ONLY the group-C checks (src/52_checksC.js) over the 557 corpus bodies and the
 * probe scenes, and compares against the Python fork (commit 8dd0d3e):
 *   - corpus: Python validate_semantic reports cached in <scratch>/jsport-node/py_reports.json
 *     (created by jsport-node/py_reports.py through python3 -I if missing)
 *   - probes: harness/py-dump.py run live through python3 -I on the probes directory
 * Comparison per body, restricted to group-C check ids:
 *   1. multiset of (section, id)                                  -> "agree"
 *   2. ordered sequence of (section, id, full message) per level              -> "exact"
 *      (group C has no set-iteration order dependence; the empty-group multiset rule is kept inert)
 * Usage: node harness/sem_2.mjs [--json out.json] [--verbose]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const here = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(here, '..');
const require = createRequire(import.meta.url);
const shim = require('./node-shim.cjs');

const SCRATCH = '/tmp/claude-0/-home-user/d1db4f4e-b69c-59c1-8b63-a13c27f16e5d/scratchpad';
const FORK = SCRATCH + '/fork-main';
const PY_REPORTS = SCRATCH + '/jsport-node/py_reports.json';
const PY_REPORTS_SCRIPT = SCRATCH + '/jsport-node/py_reports.py';
const PROBES_DIR = path.join(here, 'probes', 'C numeric-arrays (src',
  '52_checksC.js): check_interpolator_keys, check_tuple_counts, check_gaussian_splats, check_rigid_body_physics');
const PROBES_PY = SCRATCH + '/jsport-node/py_probes_C.json';

const args = process.argv.slice(2);
const verbose = args.includes('--verbose');
const jsonOut = args.includes('--json') ? args[args.indexOf('--json') + 1] : null;

// ---- library
const X3DVAL = await shim.ready({ files: ['00_ns', '10_py', '20_parse', '30_uom', '52_checksC'] });
const { t, py, uom, checks, checksC } = X3DVAL._m;
const MY_IDS = new Set(checksC.ids);
const LEVEL_OF = { Errors: 'error', Warnings: 'warning', Info: 'info' };

function runC(xml) {
  let root;
  try { root = t.parseSnapshot(xml, t.SEM_OPTS); } catch (e) { return { status: 'parse-error', detail: t.parseErrorString(e), diags: [] }; }
  const scene = t.findScene(root);
  if (!scene) return { status: 'no-scene', diags: [] };
  const diags = [];
  const ctx = { root, scene, version: t.get(root, 'version', ''), uom, py, t, emit: (level, check, message) => diags.push({ level, check, message }) };
  try { for (const fn of checksC.functions) checks[fn](ctx); }
  catch (e) { return { status: 'exception', detail: String(e && e.message || e), diags }; }   // mirrors an uncaught Python exception (OverflowError)
  return { status: 'report', diags };
}

// Parse a Python markdown report into [{level, check, message}] keeping order. Messages are
// printed raw by Python (never escaped), so an attribute value with a newline produces a
// multi-line item: items are split on "\n- **[" boundaries, sections on "\n## <Level>\n\n".
function parsePy(report) {
  const out = [];
  const parts = report.split(/\n## (Errors|Warnings|Info)\n\n/);
  for (let i = 1; i < parts.length; i += 2) {
    const level = LEVEL_OF[parts[i]];
    let body = parts[i + 1];
    if (parts[i] !== 'Info') body = body.replace(/\n$/, '');   // Errors/Warnings end with a separator "" line; Info does not
    for (const item of body.split(/\n(?=- \*\*\[)/)) {
      if (!item.startsWith('- **[')) continue;
      const close = item.indexOf(']** ');
      if (close < 0) continue;
      out.push({ level, check: item.slice(5, close), message: item.slice(close + 4) });
    }
  }
  return out;
}
const firstLine = s => s;   // full message (multi-line included)
const key2 = d => d.level + ' ' + d.check;
const key3 = d => d.level + ' ' + d.check + ' ' + firstLine(d.message);
const sortedJoin = arr => arr.slice().sort().join('\u0001');

function compare(pyDiags, jsDiags) {
  const pyA = pyDiags.filter(d => MY_IDS.has(d.check));
  const agree = sortedJoin(pyA.map(key2)) === sortedJoin(jsDiags.map(key2));
  // Python's report groups diagnostics by level (Errors, Warnings, Info) keeping emission order
  // inside each group, so the ordered comparison is per level.
  let exact = true;
  for (const level of ['error', 'warning', 'info']) {
    const seqPy = pyA.filter(d => d.level === level && d.check !== 'empty-group').map(key3).join('\u0002');
    const seqJs = jsDiags.filter(d => d.level === level && d.check !== 'empty-group').map(key3).join('\u0002');
    const egPy = sortedJoin(pyA.filter(d => d.level === level && d.check === 'empty-group').map(key3));
    const egJs = sortedJoin(jsDiags.filter(d => d.level === level && d.check === 'empty-group').map(key3));
    if (seqPy !== seqJs || egPy !== egJs) exact = false;
  }
  return { agree, exact, pyA };
}
function diffDetail(pyA, jsDiags) {
  const p = pyA.map(key3), j = jsDiags.map(key3);
  const pc = new Map(), jc = new Map();
  for (const x of p) pc.set(x, (pc.get(x) || 0) + 1);
  for (const x of j) jc.set(x, (jc.get(x) || 0) + 1);
  const onlyPy = [], onlyJs = [];
  for (const [x, n] of pc) if ((jc.get(x) || 0) < n) onlyPy.push(x);
  for (const [x, n] of jc) if ((pc.get(x) || 0) < n) onlyJs.push(x);
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

const result = { label: X3DVAL.label, checks: checksC.ids, agree: { bodies: 0, total: 0, exact: 0, probes: 0, probes_total: 0, probes_exact: 0 }, disagreements: [], inexact: [], ms: { total: 0, max: 0 } };
let statusCounts = { report: 0, 'parse-error': 0, 'no-scene': 0, exception: 0 };
for (const [k, xml] of bodies) {
  result.agree.total++;
  const t0 = performance.now();
  const r = runC(xml);
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
  if (c.agree) result.agree.bodies++;
  if (c.exact) result.agree.exact++;
  if (!c.agree || !c.exact) {
    const d = diffDetail(c.pyA, r.diags);
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
      const r = runC(xml);
      const rep = pyProbes[dirKey + '/' + f].semantic;
      const pyD = parsePy(rep);
      const okStatus = r.status === 'report' ? !rep.startsWith('# Semantic Check: Parse Error') && !rep.startsWith('# Semantic Check: No Scene')
        : rep.startsWith('# Semantic Check: ' + (r.status === 'parse-error' ? 'Parse Error' : 'No Scene'));
      const c = compare(pyD, r.diags);
      const agree = okStatus && c.agree, exact = okStatus && c.exact;
      if (agree) result.agree.probes++;
      if (exact) result.agree.probes_exact++;
      const row = { probe: f, status: r.status, agree, exact, n_py: c.pyA.length, n_js: r.diags.length };
      if (!exact) { const d = diffDetail(c.pyA, r.diags); row.py = d.onlyPy; row.js = d.onlyJs; row.py_report = rep; row.js_diags = r.diags; result.disagreements.push({ key: 'probe/' + f, check: [...new Set([...d.onlyPy, ...d.onlyJs].map(x => x.split(' ')[1]))].join(','), py: d.onlyPy, js: d.onlyJs }); }
      if (verbose) row.js_diags = r.diags, row.py_report = rep;
      result.probes.push(row);
    }
  }
}

result.ms.avg = result.ms.total / Math.max(1, result.agree.total);
if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(result, null, 1));
const summary = { agree: result.agree, status_counts: statusCounts, ms_avg: +result.ms.avg.toFixed(3), ms_max: +result.ms.max.toFixed(1), disagreements: result.disagreements.length, inexact: result.inexact.length };
console.log(JSON.stringify(summary));
if (verbose || result.disagreements.length || result.inexact.length) {
  for (const d of result.disagreements.slice(0, 40)) console.log('DISAGREE', JSON.stringify(d));
  for (const d of result.inexact.slice(0, 40)) console.log('INEXACT', JSON.stringify(d));
}
process.exitCode = result.disagreements.length ? 1 : 0;
