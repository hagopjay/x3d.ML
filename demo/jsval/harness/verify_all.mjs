/* Whole-port verification harness (js-port-of-8dd0d3e, round 0).
 *
 * Runs the shipped x3dval.js (through node_shim.mjs) over all 557 corpus bodies and every probe
 * scene under harness/probes/** and compares with the Python fork at 8dd0d3e on four levels:
 *   (a) overall valid            = xsd.valid && no semantic error lines (canary/verdicts.py rule)
 *   (b) XSD valid + error count   (+ full validate_xml dict byte-equality, reported separately)
 *   (c) semantic (section,id) multiset (+ status header: Parse Error / No Scene / All Clear / Report)
 *   (d) full report text byte-equality (+ equality modulo empty-group ordering, which in Python
 *       depends on PYTHONHASHSEED because _check_empty_groups iterates a set)
 * Python reference: <scratch>/jsport-node/py_full.json (py-dump.py corpus dump, created with python3 -I
 * if missing); probes are dumped live with py-dump.py per directory. Extra in-memory synthetic cases
 * (too big or too odd to keep as files) are written to the scratchpad and dumped the same way.
 *
 * Usage: node harness/verify_all.mjs [--json out.json] [--md out.md] [--no-probes] [--no-big]
 */
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { X3DVAL, load, ROOT } from './node_shim.mjs';

const SCRATCH = '/tmp/claude-0/-home-user/d1db4f4e-b69c-59c1-8b63-a13c27f16e5d/scratchpad';
const FORK = SCRATCH + '/fork-main';
const PY_FULL = SCRATCH + '/jsport-node/py_full.json';
const PY_REPORTS = SCRATCH + '/jsport-node/py_reports.json';
const PY_DUMP = path.join(ROOT, 'harness', 'py-dump.py');
const SYN_DIR = SCRATCH + '/jsport-node/verify-synthetic';
const args = process.argv.slice(2);
const opt = (name) => (args.includes(name) ? args[args.indexOf(name) + 1] : null);
const jsonOut = opt('--json'), mdOut = opt('--md');
const noProbes = args.includes('--no-probes'), noBig = args.includes('--no-big');
const dec = new TextDecoder('utf-8'); // errors="replace" like Python's open(..., errors="replace")

// ---------------------------------------------------------------- load + timing
const tLoad0 = performance.now();
await load();
const loadOnlyMs = performance.now() - tLoad0;
const compile40 = X3DVAL.precompile('4.0');
const compile41 = X3DVAL.precompile('4.1');
const loadMs = loadOnlyMs + compile40; // what a page waits for before its first 4.0 verdict

// ---------------------------------------------------------------- Python reference
function pyDump(outFile, dirs) {
  execFileSync('python3', ['-I', PY_DUMP, FORK, outFile, ...dirs], { cwd: SCRATCH + '/canary', stdio: ['ignore', 'ignore', 'inherit'], maxBuffer: 1 << 28 });
  return JSON.parse(fs.readFileSync(outFile, 'utf8'));
}
if (!fs.existsSync(PY_FULL)) pyDump(PY_FULL, []);
const pyFull = JSON.parse(fs.readFileSync(PY_FULL, 'utf8'));
const pyReports = fs.existsSync(PY_REPORTS) ? JSON.parse(fs.readFileSync(PY_REPORTS, 'utf8')) : null;

// ---------------------------------------------------------------- bodies
const bodies = new Map();
for (const it of JSON.parse(fs.readFileSync('/home/user/x3d.ml/demo/data/replay.json', 'utf8'))) bodies.set('replay/' + it.k, it.b);
const liveRoot = '/home/user/x3d.ml/runs/live-2026-10-17/x3d';
const liveFiles = [];
for (const model of fs.readdirSync(liveRoot)) for (const f of fs.readdirSync(path.join(liveRoot, model))) if (f.endsWith('.x3d')) liveFiles.push(path.join(liveRoot, model, f));
liveFiles.sort();
for (const f of liveFiles) bodies.set('live/' + f.split('/').slice(-2).join('/'), dec.decode(fs.readFileSync(f)));

// ---------------------------------------------------------------- comparison helpers
const { parseReport } = X3DVAL._m.report;
const statusOf = (rep) => rep.startsWith('# Semantic Check: Parse Error') ? 'parse-error'
  : rep.startsWith('# Semantic Check: No Scene') ? 'no-scene'
  : rep.startsWith('# Semantic Check: All Clear') ? 'all-clear' : 'report';
const sortedJoin = (arr) => arr.slice().sort().join('\u0001');
const pyValid = (ref) => !!ref.validate.valid && !parseReport(ref.semantic).some(d => d.level === 'error');

function modEmptyGroup(rep) {
  // canonical form: within each level, keep order of everything except empty-group items, which are sorted
  const diags = parseReport(rep);
  const out = [];
  for (const level of ['error', 'warning', 'info']) {
    const seq = diags.filter(d => d.level === level && d.check !== 'empty-group').map(d => d.check + '\u0003' + d.message);
    const eg = diags.filter(d => d.level === level && d.check === 'empty-group').map(d => d.message).sort();
    out.push(level + ':' + seq.join('\u0002') + '|' + eg.join('\u0002'));
  }
  return statusOf(rep) + '\n' + out.join('\n');
}

function compareOne(key, xml, ref, group) {
  const r = X3DVAL.validate(xml);
  const row = { key, group, ms: r.ms, a: false, b: false, b_full: false, c: false, d: false, d_mod_eg: false, issues: [] };
  // Python raised instead of returning (py-dump.py records {"exception": "Type: msg"}): the port must report
  // status 'exception' on the same side (xsd and/or semantic) -- and nothing else is comparable for that side.
  const pyXsdExc = ref.validate && ref.validate.exception, pySemExc = typeof ref.semantic !== 'string' ? ref.semantic.exception : null;
  if (pyXsdExc || pySemExc) {
    const jsXsdExc = r.xsd.status === 'exception' ? r.xsd.error : null, jsSemExc = r.semantic.status === 'exception' ? r.semantic.error : null;
    const okX = !!pyXsdExc === !!jsXsdExc, okS = !!pySemExc === !!jsSemExc;
    row.a = row.b = row.b_full = row.c = row.d = row.d_mod_eg = okX && okS && r.valid === false;
    if (!okX) row.issues.push({ level: 'b', check: '*xsd-exception', py: pyXsdExc || JSON.stringify(ref.validate).slice(0, 200), js: jsXsdExc || JSON.stringify(r.xsd).slice(0, 200) });
    if (!okS) row.issues.push({ level: 'c', check: '*sem-exception', py: pySemExc || String(ref.semantic).split('\n')[0], js: jsSemExc || r.semantic.status });
    if (okX && okS) row.issues.push({ level: 'exception', check: pyXsdExc ? '*xsd-exception' : '*sem-exception', py: pyXsdExc || pySemExc, js: jsXsdExc || jsSemExc });
    return row;
  }
  if (r.xsd.status === 'exception' || r.semantic.status === 'exception') {
    row.issues.push({ level: r.xsd.status === 'exception' ? 'b' : 'c', check: '*js-only-exception', py: 'returned', js: r.xsd.error || r.semantic.error });
    return row;
  }
  // (a)
  const pv = pyValid(ref);
  row.a = pv === r.valid;
  if (!row.a) row.issues.push({ level: 'a', check: '*valid', py: String(pv), js: String(r.valid) });
  // (b)
  const pyX = ref.validate, jsX = r.xsd;
  row.b = !!pyX.valid === !!jsX.valid && (pyX.errors || []).length === (jsX.errors || []).length;
  row.b_full = JSON.stringify(pyX) === JSON.stringify(jsX);
  if (!row.b) row.issues.push({ level: 'b', check: '*xsd', py: JSON.stringify({ valid: pyX.valid, n: (pyX.errors || []).length, first: (pyX.errors || [])[0] }), js: JSON.stringify({ valid: jsX.valid, n: (jsX.errors || []).length, first: (jsX.errors || [])[0] }) });
  else if (!row.b_full) {
    const pe = pyX.errors || [], je = jsX.errors || [];
    let i = 0; while (i < pe.length && pe[i] === je[i]) i++;
    const pn = JSON.stringify(pyX.notes || null), jn = JSON.stringify(jsX.notes || null);
    row.issues.push({ level: 'b-full', check: '*xsd-dict', py: i < pe.length ? pe[i] : (pn !== jn ? 'notes=' + pn : 'schema_version=' + pyX.schema_version), js: i < je.length ? je[i] : (pn !== jn ? 'notes=' + jn : 'schema_version=' + jsX.schema_version) });
  }
  // (c)
  const pyRep = ref.semantic, jsRep = r.semantic.report;
  const pyD = parseReport(pyRep), jsD = parseReport(jsRep);
  const sameStatus = statusOf(pyRep) === r.semantic.status || (r.semantic.status === 'exception');
  row.c = sameStatus && r.semantic.status !== 'exception' && sortedJoin(pyD.map(d => d.level + ' ' + d.check)) === sortedJoin(jsD.map(d => d.level + ' ' + d.check));
  if (!row.c) {
    if (r.semantic.status === 'exception') row.issues.push({ level: 'c', check: '*exception', py: pyRep.split('\n')[0], js: 'exception: ' + r.semantic.error });
    else if (!sameStatus) row.issues.push({ level: 'c', check: '*status', py: pyRep.split('\n')[0], js: r.semantic.status });
    else {
      const pc = new Map(), jc = new Map();
      for (const d of pyD) { const k = d.level + ' ' + d.check; pc.set(k, (pc.get(k) || 0) + 1); }
      for (const d of jsD) { const k = d.level + ' ' + d.check; jc.set(k, (jc.get(k) || 0) + 1); }
      const keys = new Set([...pc.keys(), ...jc.keys()]);
      for (const k of keys) if ((pc.get(k) || 0) !== (jc.get(k) || 0)) row.issues.push({ level: 'c', check: k.split(' ')[1], py: String(pc.get(k) || 0) + 'x', js: String(jc.get(k) || 0) + 'x' });
    }
  }
  // (d)
  row.d = pyRep === jsRep;
  row.d_mod_eg = row.d || modEmptyGroup(pyRep) === modEmptyGroup(jsRep);
  if (!row.d && row.c) {
    // find the first differing diagnostic (per level sequence) for the table
    const pm = new Map(), jm = new Map();
    for (const d of pyD) { const k = d.level + ' ' + d.check + ' ' + d.message; pm.set(k, (pm.get(k) || 0) + 1); }
    for (const d of jsD) { const k = d.level + ' ' + d.check + ' ' + d.message; jm.set(k, (jm.get(k) || 0) + 1); }
    const onlyPy = [...pm].filter(([k, n]) => (jm.get(k) || 0) < n).map(([k]) => k);
    const onlyJs = [...jm].filter(([k, n]) => (pm.get(k) || 0) < n).map(([k]) => k);
    if (onlyPy.length || onlyJs.length) {
      const checks = new Set([...onlyPy, ...onlyJs].map(k => k.split(' ')[1]));
      for (const ch of checks) row.issues.push({ level: 'd', check: ch, py: onlyPy.filter(k => k.split(' ')[1] === ch).join(' || '), js: onlyJs.filter(k => k.split(' ')[1] === ch).join(' || ') });
    } else if (row.d_mod_eg) {
      row.issues.push({ level: 'd-order', check: 'empty-group', py: pyD.filter(d => d.check === 'empty-group').map(d => d.message).join(' || '), js: jsD.filter(d => d.check === 'empty-group').map(d => d.message).join(' || ') });
    } else {
      // same multiset of full items, different order of non-empty-group items (or a header difference)
      let i = 0; const pl = pyRep.split('\n'), jl = jsRep.split('\n');
      while (i < pl.length && pl[i] === jl[i]) i++;
      row.issues.push({ level: 'd-order', check: (pl[i] || '').match(/\*\*\[([^\]]+)\]/)?.[1] || '*header', py: pl[i], js: jl[i] });
    }
  }
  return row;
}

// ---------------------------------------------------------------- corpus run
const rows = [];
const timings = [];
let i = 0;
for (const [k, xml] of bodies) {
  const ref = pyFull[k];
  if (!ref) { rows.push({ key: k, group: 'corpus', issues: [{ level: 'ref', check: '*missing-python-ref', py: '-', js: '-' }] }); continue; }
  const row = compareOne(k, xml, ref, 'corpus');
  timings.push(row.ms);
  rows.push(row);
  i++;
}
// second pass for steady-state timing (first pass includes JIT warm-up)
const timings2 = [];
for (const [, xml] of bodies) timings2.push(X3DVAL.validate(xml).ms);
const q = (arr, p) => { const s = arr.slice().sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };

// Python-vs-Python: how many corpus reports differ between the two Python runs (hash-seed order of empty-group)
let pyPyDiff = 0, pyPyDiffModEg = 0;
if (pyReports) for (const k of Object.keys(pyFull)) { if (pyReports[k] !== undefined && pyReports[k] !== pyFull[k].semantic) { pyPyDiff++; if (modEmptyGroup(pyReports[k]) !== modEmptyGroup(pyFull[k].semantic)) pyPyDiffModEg++; } }

// ---------------------------------------------------------------- probes
const probeRows = [];
const probeDirs = [];
if (!noProbes) {
  const walk = (d) => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p); else if (e.name.endsWith('.x3d')) { const dir = path.dirname(p); if (!probeDirs.includes(dir)) probeDirs.push(dir); } } };
  const pr = path.join(ROOT, 'harness', 'probes');
  if (fs.existsSync(pr)) walk(pr);
  // in-memory synthetic cases (big / odd) are materialised in the scratchpad and treated as one more probe dir
  if (!noBig) {
    fs.rmSync(SYN_DIR, { recursive: true, force: true });
    fs.mkdirSync(SYN_DIR, { recursive: true });
    const hdr = "<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Immersive' version='4.0'><head/><Scene>";
    const syn = {
      'big_01_attr_11mb.x3d': hdr + "<Shape><IndexedFaceSet coordIndex='" + '0 1 2 -1 '.repeat(1400000) + "'><Coordinate point='0 0 0 1 0 0 0 1 0'/></IndexedFaceSet></Shape></Scene></X3D>",
      'big_02_depth_300.x3d': hdr + "<Transform DEF='T'>".repeat(300) + '<Shape><Box/></Shape>' + '</Transform>'.repeat(300) + '</Scene></X3D>',
      'big_03_depth_3000.x3d': hdr + '<Group>'.repeat(3000) + '<Shape><Box/></Shape>' + '</Group>'.repeat(3000) + '</Scene></X3D>',
      'big_04_20k_shapes.x3d': hdr + Array.from({ length: 20000 }, (_, n) => `<Transform DEF='T${n}' translation='${n} 0 0'><Shape><Appearance><Material/></Appearance><Box/></Shape></Transform>`).join('') + "<ROUTE fromNode='T19999' fromField='translation_changed' toNode='T0' toField='set_translation'/></Scene></X3D>",
      'big_05_text_11mb.x3d': hdr + "<Shape><Appearance><Material/></Appearance><Box/></Shape><Script DEF='S'><![CDATA[" + 'x'.repeat(11000000) + ']]></Script></Scene></X3D>',
      'big_06_many_defs.x3d': hdr + Array.from({ length: 5000 }, (_, n) => `<Group DEF='g${n}'/>`).join('') + Array.from({ length: 5000 }, (_, n) => `<Group USE='g${(n * 7) % 5100}'/>`).join('') + '</Scene></X3D>',
      'big_07_wide_route_fanout.x3d': hdr + "<TimeSensor DEF='Clock' loop='true'/>" + Array.from({ length: 3000 }, (_, n) => `<Transform DEF='X${n}'/><ROUTE fromNode='Clock' fromField='fraction_changed' toNode='X${n}' toField='nope'/>`).join('') + '</Scene></X3D>'
    };
    for (const [f, body] of Object.entries(syn)) fs.writeFileSync(path.join(SYN_DIR, f), body);
    probeDirs.push(SYN_DIR);
  }
  let n = 0;
  for (const dir of probeDirs) {
    const files = fs.readdirSync(dir).filter(f => f.endsWith('.x3d')).sort();
    if (!files.length) continue;
    const out = SCRATCH + `/jsport-node/py_probes_verify_${n++}.json`;
    const py = pyDump(out, [dir]);
    const dirKey = path.basename(dir);
    const group = path.relative(path.join(ROOT, 'harness', 'probes'), dir).split(path.sep)[0].replace(/ \(src$/, '');
    for (const f of files) {
      const xml = dec.decode(fs.readFileSync(path.join(dir, f)));
      const ref = py[dirKey + '/' + f];
      if (!ref) { probeRows.push({ key: 'probe/' + f, group, issues: [{ level: 'ref', check: '*missing-python-ref', py: '-', js: '-' }] }); continue; }
      probeRows.push(compareOne((dir === SYN_DIR ? 'synthetic/' : 'probe/') + f, xml, ref, dir === SYN_DIR ? 'synthetic' : group));
    }
  }
}

// ---------------------------------------------------------------- exception parity (Python raises, port must not emit a report)
const exc = { xml: hdr0() + "<GaussianSplats positions='0 0 0' orientations='1e200 0 0 0'/></Scene></X3D>", py: null, js: null };
function hdr0() { return "<X3D profile='Immersive' version='4.1'><head/><Scene>"; }
try {
  exc.py = execFileSync('python3', ['-I', '-c', `
import sys; sys.path[0:0]=['${FORK}/src','${FORK}']
from validation.semantic import validate_semantic
try:
    r = validate_semantic(sys.stdin.read()); print('report:' + r.split(chr(10))[0])
except Exception as e:
    print('exception:' + type(e).__name__ + ': ' + str(e))
`], { input: exc.xml, cwd: SCRATCH + '/canary' }).toString().trim();
} catch (e) { exc.py = 'harness-error: ' + e.message; }
const er = X3DVAL.validate(exc.xml);
exc.js = er.semantic.status === 'exception' ? 'exception:' + er.semantic.error : 'report:' + er.semantic.report.split('\n')[0];
exc.agree = exc.py.startsWith('exception:') && exc.js.startsWith('exception:');

// ---------------------------------------------------------------- shipped bytes
function walkBytes(dir, rel = '') {
  let total = 0; const files = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name), r = rel + e.name;
    if (e.isDirectory()) { if (r === 'harness') continue; const w = walkBytes(p, r + '/'); total += w.total; files.push(...w.files); }
    else { const s = fs.statSync(p).size; total += s; files.push([r, s]); }
  }
  return { total, files };
}
const shipped = walkBytes(ROOT);

// ---------------------------------------------------------------- summary
const all = [...rows, ...probeRows];
const corpus = rows.filter(r => r.a !== undefined);
const summary = {
  label: X3DVAL.label, node: process.version,
  total_bodies: corpus.length,
  agree_valid: corpus.filter(r => r.a).length,
  agree_xsd: corpus.filter(r => r.b).length,
  agree_xsd_full_dict: corpus.filter(r => r.b_full).length,
  agree_sem_codes: corpus.filter(r => r.c).length,
  agree_report_text: corpus.filter(r => r.d).length,
  agree_report_mod_empty_group_order: corpus.filter(r => r.d_mod_eg).length,
  python_vs_python_report_diffs: pyReports ? { differing: pyPyDiff, differing_beyond_empty_group_order: pyPyDiffModEg } : null,
  probes_total: probeRows.length,
  probes_agree: probeRows.filter(r => r.a && r.b && r.c && r.d).length,
  probes_agree_mod_eg: probeRows.filter(r => r.a && r.b && r.c && r.d_mod_eg).length,
  probe_dirs: probeDirs.map(d => path.basename(d) + ' (' + fs.readdirSync(d).filter(f => f.endsWith('.x3d')).length + ')'),
  exception_parity: exc,
  load_ms: +loadMs.toFixed(0), load_only_ms: +loadOnlyMs.toFixed(0), compile_ms: { '4.0': +compile40.toFixed(0), '4.1': +compile41.toFixed(0) },
  validate_ms_first_pass: { median: +q(timings, 0.5).toFixed(3), p90: +q(timings, 0.9).toFixed(3), max: +Math.max(...timings).toFixed(1) },
  validate_ms_second_pass: { median: +q(timings2, 0.5).toFixed(3), p90: +q(timings2, 0.9).toFixed(3), max: +Math.max(...timings2).toFixed(1) },
  bytes: shipped.total,
  bytes_breakdown: Object.fromEntries(shipped.files.filter(([, s]) => s > 50000).map(([f, s]) => [f, s]))
};
const issues = [];
for (const r of all) for (const is of r.issues || []) issues.push({ key: r.key, group: r.group, ...is });
summary.issue_count = issues.length;

if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify({ summary, issues, rows: all.map(r => ({ key: r.key, group: r.group, a: r.a, b: r.b, b_full: r.b_full, c: r.c, d: r.d, d_mod_eg: r.d_mod_eg, ms: r.ms })) }, null, 1));

// ---------------------------------------------------------------- markdown table grouped by check
if (mdOut) {
  const esc = (s) => String(s ?? '').replace(/\|/g, '\\|').replace(/\n/g, '\\n').slice(0, 400);
  const byCheck = new Map();
  for (const is of issues) { const k = is.check; if (!byCheck.has(k)) byCheck.set(k, []); byCheck.get(k).push(is); }
  const L = [];
  L.push('# verify-round0 -- js-port-of-8dd0d3e vs Python fork 8dd0d3e', '');
  L.push('Generated by harness/verify_all.mjs on ' + new Date().toISOString() + ' (' + process.version + ').', '');
  L.push('## Summary', '', '```json', JSON.stringify(summary, null, 1), '```', '');
  L.push('## Disagreements grouped by check (' + issues.length + ' rows; a=valid, b=xsd, c=semantic codes, d=report text, d-order=same items different order, b-full=xsd dict detail, exception=both sides raised)', '');
  if (!issues.length) L.push('_None._', '');
  for (const [check, list] of [...byCheck].sort((x, y) => y[1].length - x[1].length)) {
    L.push(`### ${check} (${list.length})`, '', '| body | level | Python | JS |', '|---|---|---|---|');
    for (const is of list) L.push(`| ${esc(is.key)} | ${is.level} | ${esc(is.py)} | ${esc(is.js)} |`);
    L.push('');
  }
  fs.writeFileSync(mdOut, L.join('\n'));
}

console.log(JSON.stringify(summary));
for (const is of issues.slice(0, 60)) console.log('ISSUE', JSON.stringify(is).slice(0, 600));
process.exitCode = issues.filter(i => !['d-order', 'b-full', 'exception'].includes(i.level)).length ? 1 : 0;
