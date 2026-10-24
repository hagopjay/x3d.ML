/* Synthetic edge cases for xsd.js (parse errors, namespaces, DOCTYPE entities, encodings, version hints, GeoLOD hint).
 * Regenerate expectations (from a canary dir, never inside the fork tree):
 *   python3 -I harness/synthetic-xsd/py_expected.py harness/synthetic-xsd/cases.json harness/synthetic-xsd/expected-8dd0d3e.json
 * Usage: node harness/xsd_edge.mjs [cases.json expected.json]
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const JSVAL = path.resolve(here, '..');
const casesPath = process.argv[2] || path.join(here, 'synthetic-xsd/cases.json');
const expPath = process.argv[3] || path.join(here, 'synthetic-xsd/expected-8dd0d3e.json');
const cases = JSON.parse(fs.readFileSync(casesPath, 'utf8'));
const expected = JSON.parse(fs.readFileSync(expPath, 'utf8'));
if (typeof globalThis.self === 'undefined') globalThis.self = globalThis;
require(path.join(JSVAL, 'src', '40_xsd.js'));
const xsd = globalThis.X3DVAL._m.xsd;
await xsd.load({
  base: pathToFileURL(JSVAL + path.sep).href,
  read: async (url) => new Uint8Array(fs.readFileSync(url.startsWith('file:') ? fileURLToPath(url) : url)),
  importer: (url) => import(url),
});
let ok = 0, n = 0;
for (const [k, xml] of Object.entries(cases)) {
  n++;
  const js = xsd.validateXml(xml);
  const py = expected[k];
  if (JSON.stringify(js) === JSON.stringify(py)) { ok++; console.log('SAME', k); }
  else console.log('DIFF', k, '\n  py:', JSON.stringify(py), '\n  js:', JSON.stringify(js));
}
// explicit version override (validate_xml(xml, "4.1")): Python gives the same 4.1 result
const o = xsd.validateXml("<X3D profile='Immersive' version='4.0'><Scene><Shape><GaussianSplats/></Shape></Scene></X3D>", '4.1');
const oExp = {valid:false, errors:["Line 1: Element 'GaussianSplats': This element is not expected. Expected is one of ( IS, MetadataBoolean, MetadataDouble, MetadataFloat, MetadataInteger, MetadataSet, MetadataString, Appearance, Box, Cone )."], schema_version:'4.1'};
n++; if (JSON.stringify(o) === JSON.stringify(oExp)) { ok++; console.log('SAME version-override'); } else console.log('DIFF version-override', JSON.stringify(o));
console.log(`edge parity ${ok}/${n}`);
process.exitCode = ok === n ? 0 : 1;
