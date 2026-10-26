// Headless render of a v3 scene from each viewpoint. node shoot.mjs SITE SCENE OUT W H vp1,vp2,...  [phase] [settle_ms]
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs'; import path from 'path'; import http from 'http';
const [site, scene, out, W, H, vps, phaseArg, settleArg] = process.argv.slice(2);
const phase = phaseArg === undefined ? 1 : Number(phaseArg); const settle = Number(settleArg || 4000);
fs.mkdirSync(out, { recursive: true });
const mime = { '.js': 'text/javascript', '.css': 'text/css', '.x3d': 'text/plain', '.json': 'application/json', '.wasm': 'application/wasm', '.png': 'image/png', '.html': 'text/html' };
const page0 = `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#0f0d0c}x3d-canvas{display:block;width:${W}px;height:${H}px}</style><link rel="stylesheet" href="x_ite.css"><script src="x_ite.min.js"></script></head><body><x3d-canvas id="c" splashScreen="false" notifications="false" contextMenu="false" cache="false" contentScale="1" src="${scene}"></x3d-canvas></body></html>`;
const srv = http.createServer((req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/t.html') { res.writeHead(200, { 'content-type': 'text/html' }); return res.end(page0); }
  const f = path.join(site, p);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': mime[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(res);
}).listen(0);
const port = srv.address().port;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await (await browser.newContext({ viewport: { width: +W, height: +H }, locale: 'en-US' })).newPage();
page.setDefaultTimeout(300000);
const logs = []; page.on('console', m => { const t = m.text(); logs.push(t.slice(0, 200)); }); page.on('response', r => { if (r.status() >= 400) logs.push('HTTP ' + r.status() + ' ' + r.url()); }); page.on('pageerror', e => logs.push('PAGEERR ' + String(e).slice(0, 300)));
await page.goto(`http://127.0.0.1:${port}/t.html`);
for (let i = 0; i < 900; i++) { if (await page.evaluate(() => { try { return !!document.getElementById('c').browser.currentScene.getNamedNode('Phase'); } catch (e) { return false; } })) break; await page.waitForTimeout(500); }
await page.waitForTimeout(3000);
for (const vp of vps.split(',')) {
  await page.evaluate(([vp, phase]) => { const sc = document.getElementById('c').browser.currentScene, N = n => sc.getNamedNode(n);
    for (const n of ['Intro', 'Dissolve']) N(n).enabled = false;
    const v = N(vp); const pos = v.position.copy ? v.position.copy() : v.position, ori = v.orientation.copy ? v.orientation.copy() : v.orientation;
    v.set_bind = true; v.position = pos; v.orientation = ori; N('Phase').set_fraction = phase; }, [vp, phase]);
  await page.waitForTimeout(settle);
  await page.locator('#c').screenshot({ path: path.join(out, vp + '.png') });
  console.log('shot', vp);
}
console.log(JSON.stringify(logs.slice(0, 40)));
await browser.close(); srv.close();
