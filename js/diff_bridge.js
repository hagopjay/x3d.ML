"use strict";
// Bridge for diff_internals.py: reads {fn, inputs} as JSON on stdin, applies the named x3dtrace.js helper to every input, prints JSON.
var X = require("./x3dtrace.js"), I = X.internals;
var req = JSON.parse(require("fs").readFileSync(0, "utf8"));
var fns = {
  isw: function (c) { return /[\p{L}\p{N}_]/u.test(c); },
  isd: function (c) { return /\p{Nd}/u.test(c); },
  iss: function (c) { return new RegExp("^[" + "\\t-\\r\\x1c-\\x20\\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000" + "]$", "u").test(c); },
  casefold: function (c) { return I.casefold(c.normalize("NFC")); },
  toascii: function (c) { return I.toAscii(c); },
  entity: function (c) { var r = I.unescapeEnt(c); return /[\p{L}\p{N}]/u.test(r) && r !== c ? r : null; },
  round: function (a) { return I.pyRound(a[0], a[1]); },
  repr: function (x) { return I.pyRepr(x); },
  decimals: function (x) { return X.decimals(x); },
  readings: function (s) { return I.readings(s); },
  lexw: function (s) { return X.lex(s, "prose").norms; },
  lexx: function (s) { return X.lex(s, "x3d").norms; }
};
process.stdout.write(JSON.stringify(req.inputs.map(fns[req.fn])));
