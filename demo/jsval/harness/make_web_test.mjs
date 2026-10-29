/* Generates web-test.html: a classic-script smoke page for x3dval.js (main thread + Worker) over 3 corpus bodies.
 *   node harness/make_web_test.mjs        (rewrites ../web-test.html; bodies are embedded as JSON)
 * Bodies: one valid, one with XSD + semantic errors, one malformed, chosen from the verification corpus.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const canary = JSON.parse(fs.readFileSync('/tmp/claude-0/-home-user/d1db4f4e-b69c-59c1-8b63-a13c27f16e5d/scratchpad/canary/8dd0d3e.json', 'utf8')).verdicts;
const replay = new Map(JSON.parse(fs.readFileSync('/home/user/x3d.ml/demo/data/replay.json', 'utf8')).map(it => ['replay/' + it.k, it.b]));
const pick = (pred) => { for (const [k, v] of Object.entries(canary)) if (k.startsWith('replay/') && replay.has(k) && pred(v) && replay.get(k).length < 20000) return k; };
const keys = [
  pick(v => v.valid),
  pick(v => !v.xsd && v.nxsd > 0 && v.sem && v.sem.length > 0 && !v.sem.includes('parse-error')),
  'replay/qwen3-8b/oneshot/anim-02.x3d' /* malformed: XML parse error */
];
const bodies = keys.map(k => ({ key: k, xml: replay.get(k) }));
const json = JSON.stringify(bodies).replace(/<\//g, '<\\/').replace(/<!--/g, '<\\!--');
const html = `<!doctype html>
<meta charset="utf-8">
<title>x3dval smoke</title>
<style>body{font:14px/1.4 system-ui,sans-serif;margin:16px;background:#fff;color:#111}pre{white-space:pre-wrap;word-break:break-all;background:#f4f4f4;padding:8px}</style>
<h1>x3dval.js smoke test (js-port-of-8dd0d3e)</h1>
<p id="status">loading…</p>
<pre id="out"></pre>
<script>
  window.__csp = [];
  document.addEventListener('securitypolicyviolation', function (e) { window.__csp.push(e.violatedDirective + ' ' + e.blockedURI); });
  window.__bodies = ${json};
</script>
<script src="x3dval.js"></script>
<script>
(function () {
  var status = document.getElementById('status'), out = document.getElementById('out');
  function digest(r) {
    return { valid: r.valid, xsd_valid: r.xsd.valid, xsd_errors: r.xsd.errors, schema_version: r.xsd.schema_version || null, notes: r.xsd.notes || null,
             sem_status: r.semantic.status, sem_ids: [].concat(r.semantic.errors, r.semantic.warnings, r.semantic.info).map(function (d) { return d.id; }), report: r.semantic.report };
  }
  var results = { label: X3DVAL.label, main: {}, worker: {}, timing: {} };
  var t0 = performance.now();
  X3DVAL.load({ base: './' }).then(function () {
    results.timing.load_ms = performance.now() - t0;
    var tc = performance.now(); X3DVAL.precompile('4.0'); results.timing.compile40_ms = performance.now() - tc;
    window.__bodies.forEach(function (b) { results.main[b.key] = digest(X3DVAL.validate(b.xml)); });
    status.textContent = 'main thread done; starting worker…';
    var client = X3DVAL.createWorkerClient({ base: './' });
    var tw = performance.now();
    return client.load({}).then(function () {
      results.timing.worker_load_ms = performance.now() - tw;
      return window.__bodies.reduce(function (p, b) { return p.then(function () { return client.validate(b.xml).then(function (r) { results.worker[b.key] = digest(r); }); }); }, Promise.resolve());
    }).then(function () { return client.info(); }).then(function (info) { results.worker_info = info; client.terminate(); });
  }).then(function () {
    results.csp_violations = window.__csp.slice();
    window.__results = results;
    out.textContent = JSON.stringify(results, null, 1);
    status.textContent = 'done: ' + Object.keys(results.main).length + ' bodies on main thread, ' + Object.keys(results.worker).length + ' in worker, ' + results.csp_violations.length + ' CSP violations';
  }).catch(function (e) {
    results.error = String(e && e.stack || e);
    window.__results = results;
    status.textContent = 'done: ERROR ' + (e && e.message || e);
    out.textContent = results.error;
  });
})();
</script>
`;
fs.writeFileSync(path.join(ROOT, 'web-test.html'), html);
console.log('wrote web-test.html with bodies:', keys);
