/* Browser smoke: serve demo/jsval under the viewer-like CSP, open web-test.html in headless Chromium,
 * and compare the page's main-thread and Worker results with Node (node_shim) on the same 3 bodies. */
import { spawn } from 'node:child_process';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { X3DVAL, load } from '/home/user/x3d.ml/demo/jsval/harness/node_shim.mjs';
const PORT = 8793, URL = `http://127.0.0.1:${PORT}/web-test.html`;
const srv = spawn('python3', ['/tmp/claude-0/-home-user/d1db4f4e-b69c-59c1-8b63-a13c27f16e5d/scratchpad/csp_serve.py', '/home/user/x3d.ml/demo/jsval', String(PORT)], { stdio: 'ignore' });
for (let i = 0; i < 100; i++) { try { const r = await fetch(URL); if (r.ok) break; } catch (e) { await new Promise(r => setTimeout(r, 100)); } }
const b = await chromium.launch();
const pg = await b.newPage();
const console_ = [], errs = [];
pg.on('pageerror', e => errs.push('pageerror: ' + e.message));
pg.on('console', m => { console_.push(m.type() + ': ' + m.text().slice(0, 300)); });
const t0 = Date.now();
await pg.goto(URL);
await pg.waitForFunction(() => document.getElementById('status').textContent.startsWith('done'), null, { timeout: 180000 }).catch(() => console.log('TIMEOUT waiting for done'));
const status = await pg.textContent('#status');
const res = await pg.evaluate(() => window.__results);
const ua = await pg.evaluate(() => navigator.userAgent);
await b.close(); srv.kill();
console.log('UA:', ua);
console.log('status:', status, '(wall', Date.now() - t0, 'ms)');
console.log('timing:', JSON.stringify(res.timing), 'csp_violations:', JSON.stringify(res.csp_violations), 'error:', res.error || null);
console.log('console (csp/violation/error lines):', console_.filter(l => /violat|error|refused|blocked/i.test(l)));
console.log('page errors:', errs);
await load();
const bodies = JSON.parse(await (await (async () => { const fs = await import('node:fs'); return { text: async () => fs.readFileSync('/home/user/x3d.ml/demo/jsval/web-test.html', 'utf8').match(/window\.__bodies = (\[.*?\]);\n/s)[1].replace(/<\\\//g, '</').replace(/<\\!--/g, '<!--') }; })()).text());
let agree = 0, total = 0;
for (const bdy of bodies) {
  const r = X3DVAL.validate(bdy.xml);
  const node = { valid: r.valid, xsd_valid: r.xsd.valid, xsd_errors: r.xsd.errors, schema_version: r.xsd.schema_version || null, notes: r.xsd.notes || null, sem_status: r.semantic.status, sem_ids: [].concat(r.semantic.errors, r.semantic.warnings, r.semantic.info).map(d => d.id), report: r.semantic.report };
  for (const side of ['main', 'worker']) {
    total++;
    const same = JSON.stringify(res[side][bdy.key]) === JSON.stringify(node);
    if (same) agree++;
    console.log(side, bdy.key, same ? 'IDENTICAL to Node' : 'DIFFERS', JSON.stringify({ valid: node.valid, xsd_errors: node.xsd_errors.length, sem: node.sem_status, ids: node.sem_ids.length }));
    if (!same) console.log('  browser:', JSON.stringify(res[side][bdy.key]).slice(0, 500), '\n  node:', JSON.stringify(node).slice(0, 500));
  }
}
console.log(`SMOKE ${agree}/${total} body results identical to Node; worker label: ${res.worker_info && res.worker_info.label}; compileMs(worker): ${JSON.stringify(res.worker_info && res.worker_info.compileMs)}`);
