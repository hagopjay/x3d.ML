/* js-port-of-8dd0d3e -- X3DVAL namespace.
 * Classic script: works via <script>, importScripts() in a Worker, and under Node
 * through harness/node-shim.cjs (which sets globalThis.self). Every other src/*.js
 * file is an IIFE that registers into X3DVAL._m, so files can also be loaded one by
 * one (00_ns.js first). The shipped x3dval.js is the concatenation of src/*.js.
 */
(function (g) {
  if (!g.X3DVAL) g.X3DVAL = { label: 'js-port-of-8dd0d3e', _m: { checks: {} } };
  if (!g.X3DVAL._m) g.X3DVAL._m = { checks: {} };
  if (!g.X3DVAL._m.checks) g.X3DVAL._m.checks = {};
  if (!g.X3DVAL.label) g.X3DVAL.label = 'js-port-of-8dd0d3e';
})(typeof self !== 'undefined' ? self : globalThis);
