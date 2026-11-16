"use strict";
// usage: node test_vectors.js [vectors.json]
// Runs every row of vectors.json (made from the Python engine) through x3dtrace.js and compares
// verdict, status, value_status, derivation, occurrences, span and note. Also checks findAll().
// Writes disagreements.json next to this file (or the path given as second argument).
// A row may carry "sources" ([{id,text,kind}]) instead of source_text/kind (used by the fuzz rows).
var fs = require("fs");
var path = require("path");
var X = require("./x3dtrace.js");

var file = process.argv[2] || path.join(__dirname, "vectors.json");
var outFile = process.argv[3] || path.join(__dirname, "disagreements.json");
var data = JSON.parse(fs.readFileSync(file, "utf8"));
var KEYS = ["verdict", "status", "value_status", "derivation", "occurrences", "span", "note", "source", "disambiguated_by"];   // the last two only when the row has them
var FAMILIES = ["gaik", "prose", "real", "mutated"];

function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
function policyOf(p) {
  var o = {};
  Object.keys(p || {}).forEach(function (k) { o[k] = p[k]; });
  if (o.number_tolerance !== undefined) o.number_tolerance = Number(o.number_tolerance);
  return o;
}

var stat = {};
FAMILIES.forEach(function (f) { stat[f] = { rows: 0, agree: 0, disagree: 0, error: 0, locator: 0 }; });
var out = { engine_sha256_16: data.engine_sha256_16, python: data.python, error_rows: [], field_locator_rows: [],
  disagreements: [], find_all: {} };
var fa = { checked: 0, count_ok: 0, first_ok: 0, first_by_hint: 0, fail: [] };

data.rows.forEach(function (row) {
  var st = stat[row.family] || (stat[row.family] = { rows: 0, agree: 0, disagree: 0, error: 0, locator: 0 });
  st.rows++;
  if (row.expect.error !== undefined) { st.error++; out.error_rows.push(row.id); return; }
  var sources = row.sources || [{ id: "s", text: row.source_text, kind: row.kind }];
  var claim = row.sources ? row.claim : Object.assign({}, row.claim, { source: "s" });
  var got, crashed = null;
  try {
    got = X.check(claim, sources, policyOf(row.policy));
  } catch (e) { crashed = String(e && e.stack || e); got = {}; }
  // findAll (FIND only): count and first span, whatever the value did
  var fs0 = sources.filter(function (s) { return s.id === got.source; })[0] || sources[0];   // the source the quote was found in
  if (row.expect.occurrences >= 1) {
    fa.checked++;
    var spans = X.findAll(fs0.text, fs0.kind, row.claim.quote);
    if (spans.length === row.expect.occurrences) fa.count_ok++; else fa.fail.push({ id: row.id, why: "count", got: spans.length, want: row.expect.occurrences });
    if (same(spans[0], row.expect.span)) fa.first_ok++;
    else if (spans.some(function (s) { return same(s, row.expect.span); })) fa.first_by_hint++;
    else fa.fail.push({ id: row.id, why: "first", got: spans[0], want: row.expect.span });
  }
  var bad = KEYS.filter(function (k) { return row.expect[k] !== undefined && !same(got[k], row.expect[k]); });
  if (crashed) bad = ["crash"];
  if (!bad.length) { st.agree++; return; }
  // Python chose between repeated quotes with the scene (field / path hint), which is not ported. That explains a row only when
  // Python says it used the field, its chosen span is one of the occurrences, and nothing but span, disambiguated_by and the
  // ambiguity verdict (verified -> check under ambiguous_quote_is_check) differs.
  var cause = "other";
  var verdictOnlyAmbig = bad.indexOf("verdict") < 0 || (row.policy && row.policy.ambiguous_quote_is_check && row.expect.verdict === "verified" && got.verdict === "check");
  if (row.expect.occurrences > 1 && got.occurrences === row.expect.occurrences && /field|path/.test(row.expect.disambiguated_by || "") &&
      bad.every(function (k) { return k === "span" || k === "disambiguated_by" || k === "verdict"; }) && verdictOnlyAmbig &&
      X.findAll(fs0.text, fs0.kind, row.claim.quote).some(function (s) { return same(s, row.expect.span); }))
    cause = "field locator not ported";
  else if (bad.length === 1 && bad[0] === "span" && row.expect.occurrences > 1 && got.occurrences === row.expect.occurrences && /@/.test(row.claim.field || "") &&
      fs0.kind === "x3d" && /^\s*</.test(fs0.text) &&
      X.findAll(fs0.text, fs0.kind, row.claim.quote).some(function (s) { return same(s, row.expect.span); }))
    cause = "field locator not ported";   // the hint narrowed to several candidates, so Python reports no disambiguated_by
  if (cause !== "other") { st.locator++; out.field_locator_rows.push(row.id); } else st.disagree++;
  var pick = function (o) { var r = {}; KEYS.forEach(function (k) { if (row.expect[k] !== undefined) r[k] = o[k]; }); return r; };
  out.disagreements.push({ id: row.id, family: row.family, cause: cause, differs: bad, claim: row.claim, policy: row.policy,
    kind: row.kind, expect: row.expect, got: crashed ? { crash: crashed } : pick(got) });
});

var tot = { rows: 0, agree: 0, disagree: 0, error: 0, locator: 0 };
console.log("family    rows  error  compared  agree  disagree  locator  agreement(compared)  agreement(excl. locator)");
Object.keys(stat).forEach(function (f) {
  var s = stat[f], n = s.rows - s.error, pct = n ? (100 * s.agree / n).toFixed(2) : "n/a";
  var pct2 = n - s.locator ? (100 * s.agree / (n - s.locator)).toFixed(2) : "n/a";
  Object.keys(tot).forEach(function (k) { tot[k] += s[k]; });
  console.log(f.padEnd(9), String(s.rows).padStart(5), String(s.error).padStart(6), String(n).padStart(9),
    String(s.agree).padStart(6), String(s.disagree).padStart(9), String(s.locator).padStart(8), (pct + "%").padStart(20), (pct2 + "%").padStart(25));
});
var n = tot.rows - tot.error;
console.log("all".padEnd(9), String(tot.rows).padStart(5), String(tot.error).padStart(6), String(n).padStart(9),
  String(tot.agree).padStart(6), String(tot.disagree).padStart(9), String(tot.locator).padStart(8),
  ((100 * tot.agree / n).toFixed(2) + "%").padStart(20), ((100 * tot.agree / (n - tot.locator)).toFixed(2) + "%").padStart(25));
console.log("engine crashes skipped:", out.error_rows.length, out.error_rows.slice(0, 30).join(" "));
console.log("findAll: rows with occurrences >= 1:", fa.checked, "| count equals expect.occurrences:", fa.count_ok, "| first span equals expect.span:", fa.first_ok,
  "| expect.span is a later occurrence (Python chose by field/path hint):", fa.first_by_hint, "| failures:", fa.fail.length);
fa.fail.slice(0, 10).forEach(function (f) { console.log("  findAll FAIL", JSON.stringify(f)); });
out.find_all = fa;
out.summary = { stat: stat, total: tot };
fs.writeFileSync(outFile, JSON.stringify(out, null, 1));
var real = out.disagreements.filter(function (d) { return d.cause === "other"; });
console.log("disagreements written:", real.length, "(+", out.field_locator_rows.length, "field locator rows) ->", path.basename(outFile));
real.slice(0, 25).forEach(function (d) {
  console.log(d.id, d.differs.join(","), "|", JSON.stringify(d.claim.value), "|", JSON.stringify(d.claim.quote).slice(0, 70),
    "\n   py:", JSON.stringify(d.expect), "\n   js:", JSON.stringify(d.got));
});
process.exitCode = real.length || fa.fail.length ? 1 : 0;
