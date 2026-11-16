/* x3dtrace.js - JavaScript port of x3dtrace.py: FIND, COMPARE and LOCATE for one claim.
 * Dependency free, ES2018, no DOM. Plain <script> -> window.X3DTrace; CommonJS -> module.exports.
 *
 *   X3DTrace.check(claim, sources, policy) -> {verdict, status, value_status, derivation, occurrences, span, note, ...}
 *       claim   {field, value, quote, source?, ftype?, prefix?, suffix?, line?}
 *       sources [{id, text, kind: "text"|"x3d"}]       policy: keys of TracePolicy (all optional)
 *   X3DTrace.findAll(text, kind, quote[, utf16]) -> [[start, end], ...] every whole-token occurrence, document order
 *
 * Offsets (span, findAll) count Unicode code points, like Python. `span16` and findAll(..., true) count UTF-16 units
 * (what String.slice wants). The two agree unless the text holds characters outside the BMP.
 *
 * Ported from the engine revision "v4" (the fixes listed in docs/TRACE-REVIEW.md). Not ported: the SceneIndex
 * based choice between repeated quotes (field / path hints; prefix, suffix and line hints are ported); HTML named entities
 * outside the HTML 4 set (such an entity is skipped as a token instead of being read as its letter).
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module && module.exports) module.exports = api;
  else root.X3DTrace = api;
})(typeof window !== "undefined" ? window : typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // ---- Python character classes (Python's \s, \w, \d are Unicode aware, JavaScript's are not) --------------------
  var S = "\\t-\\r\\x1c-\\x20\\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000";   // str.isspace
  var W = "\\p{L}\\p{N}_";   // \w
  var D = "\\p{Nd}";         // \d
  var NOTW = "(?![" + W + "])";   // \b after a word character
  function table(o) { return Object.assign(Object.create(null), o); }   // no inherited keys such as "constructor"
  function strip(s) { return s.replace(RE_STRIP, ""); }
  function toAscii(s) {   // Unicode decimal digits -> 0-9 (Python float(), int() and Decimal() accept them)
    return s.replace(/\p{Nd}/gu, function (ch) {
      var cp = ch.codePointAt(0), z = cp;
      if (cp < 128) return ch;
      while (z > 0 && /\p{Nd}/u.test(String.fromCodePoint(z - 1))) z--;
      return String((cp - z) % 10);
    });
  }
  function casefold(s) {   // str.casefold: upper then lower, with the places where that differs
    return s.split("\u0131").map(function (p) {
      return p.replace(/\u1e9e/g, "ss").toUpperCase().toLowerCase().replace(/\u03c2/g, "\u03c3")
        .replace(/[\u13f8-\u13fd\uab70-\uabbf]/g, function (c) { return c.toUpperCase(); });
    }).join("\u0131");
  }
  var RE_STRIP = new RegExp("^[" + S + "]+|[" + S + "]+$", "gu");
  var RE_SPLIT = new RegExp("[" + S + ",]+", "u");

  // ---- policy ---------------------------------------------------------------------------------------------------------
  var ALL_CONVERSIONS = ["deg2rad", "rad2deg", "percent", "rgb255", "hex", "colorname", "numword", "unit", "broadcast", "axis"];
  function makePolicy(p) {
    var d = { number_tolerance: 1e-6, round_to_printed: true, match_reformatted_identifiers: true, reworded_is_problem: false,
      min_quote_words: 1, ambiguous_quote_is_check: false, moved_is_check: false, code_values_unchecked: false,
      conversions: ALL_CONVERSIONS.slice(), length_scale: 1 };
    Object.keys(p || {}).forEach(function (k) { if (Object.prototype.hasOwnProperty.call(d, k)) d[k] = p[k]; });
    d.number_tolerance = Number(d.number_tolerance);
    d.length_scale = Number(d.length_scale);
    d.conversions = Array.from(d.conversions);
    return d;
  }
  function strictPolicy() {
    return makePolicy({ reworded_is_problem: true, ambiguous_quote_is_check: true, moved_is_check: true, conversions: [], round_to_printed: false });
  }
  function allows(pol, name) { return pol.conversions.indexOf(name) >= 0; }

  // ---- lexer: number aware tokens with offsets --------------------------------------------------------------------------
  // combining marks (Mn, Mc, Me) up to U+1FFFF, as the engine builds its class from the Unicode database; plus the soft hyphen
  var MARK = "(?:(?![\\u{20000}-\\u{10ffff}])\\p{M}|\\u00ad)";
  var ENT = "&(?:#" + D + "+|#[xX][0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);";
  var NUM_X3D = "(?<![" + W + ".])[+-]?(?:" + D + "+\\.?" + D + "*|\\." + D + "+)(?:[eE][+-]?" + D + "+)?(?!" + D + ")";
  var NUM_PROSE = "(?<![" + W + ".,])[+-]?(?:" + D + "+(?:[.,'\\u2019]" + D + "+)*|[.,]" + D + "+)(?:[eE][+-]?" + D + "+)?(?!" + D + ")";
  var LEX_RE = {
    x3d: new RegExp("(?<ent>" + ENT + ")|(?<num>" + NUM_X3D + ")|(?<word>(?:[" + W + "]|" + MARK + ")+)", "gu"),
    prose: new RegExp("(?<num>" + NUM_PROSE + ")|(?<word>(?:[\\p{L}\\p{N}]|" + MARK + ")+)", "gu")
  };
  // HTML 4 named entities whose text holds a letter or digit (the rest are skipped either way)
  var NAMED = table({ OElig: "\u0152", oelig: "\u0153", Scaron: "\u0160", scaron: "\u0161", Yuml: "\u0178", fnof: "\u0192",
    thetasym: "\u03d1", upsih: "\u03d2", piv: "\u03d6" });
  ("nbsp iexcl cent pound curren yen brvbar sect uml copy ordf laquo not shy reg macr deg plusmn sup2 sup3 acute micro para " +
    "middot cedil sup1 ordm raquo frac14 frac12 frac34 iquest Agrave Aacute Acirc Atilde Auml Aring AElig Ccedil Egrave Eacute " +
    "Ecirc Euml Igrave Iacute Icirc Iuml ETH Ntilde Ograve Oacute Ocirc Otilde Ouml times Oslash Ugrave Uacute Ucirc Uuml Yacute " +
    "THORN szlig agrave aacute acirc atilde auml aring aelig ccedil egrave eacute ecirc euml igrave iacute icirc iuml eth ntilde " +
    "ograve oacute ocirc otilde ouml divide oslash ugrave uacute ucirc uuml yacute thorn yuml").split(" ")
    .forEach(function (n, i) { NAMED[n] = String.fromCharCode(160 + i); });
  [[913, "Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Lambda Mu Nu Xi Omicron Pi Rho"],
    [931, "Sigma Tau Upsilon Phi Chi Psi Omega"],
    [945, "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigmaf sigma tau upsilon phi chi psi omega"]]
    .forEach(function (g) { g[1].split(" ").forEach(function (n, i) { NAMED[n] = String.fromCharCode(g[0] + i); }); });
  var CP1252 = "\u20ac\x81\u201a\u0192\u201e\u2026\u2020\u2021\u02c6\u2030\u0160\u2039\u0152\x8d\u017d\x8f\x90\u2018\u2019\u201c\u201d\u2022\u2013\u2014\u02dc\u2122\u0161\u203a\u0153\x9d\u017e\u0178";
  function unescapeEnt(raw) {   // html.unescape for one entity with its semicolon
    var m = /^&#([0-9]+);$/.exec(raw), cp;
    if (m) cp = parseInt(m[1], 10);
    else if ((m = /^&#[xX]([0-9a-fA-F]+);$/.exec(raw))) cp = parseInt(m[1], 16);
    else return NAMED[raw.slice(1, -1)] || raw;
    if (cp >= 0x80 && cp <= 0x9f) return CP1252.charAt(cp - 0x80);
    if (cp === 0 || (cp >= 0xd800 && cp <= 0xdfff) || cp > 0x10ffff) return "\ufffd";
    return String.fromCodePoint(cp);
  }
  function lex(text, mode, normalizer) {
    var rx = LEX_RE[mode], t = text.replace(/[\u2212\u2013]/g, "-"), m, raw, n, kind;
    var L = { text: text, mode: mode, norms: [], starts: [], ends: [], kinds: [] };
    rx.lastIndex = 0;
    while ((m = rx.exec(t)) !== null) {
      raw = m[0];
      if (m.groups.ent !== undefined) {
        var dec = unescapeEnt(raw);
        if (dec === raw || !/[\p{L}\p{N}]/u.test(dec)) continue;
        raw = dec; kind = "w";
      } else kind = m.groups.num !== undefined ? "n" : "w";
      if (kind === "n") {
        n = raw.toLowerCase();
        if (n.charAt(0) === "+") n = n.slice(1);
      } else {
        n = raw.replace(/\u00ad/g, "").normalize("NFC");
        if (mode === "prose") n = casefold(n);
        if (normalizer) n = normalizer(n);
        if (!n) continue;
      }
      L.norms.push(n); L.starts.push(m.index); L.ends.push(m.index + m[0].length); L.kinds.push(kind);
    }
    return L;
  }
  function sniffKind(text) {
    var t = text.replace(/^[\ufeff \t\r\n]+/, "").slice(0, 600);
    if (/^(<\?xml|<X3D|#X3D|#VRML)/.test(t)) return "x3d";
    return t.charAt(0) === "{" && t.indexOf('"X3D"') >= 0 ? "x3d" : "text";
  }

  // ---- sources and whole-token run search ----------------------------------------------------------------------------------
  function makeSource(s) {
    var kind = !s.kind || s.kind === "auto" ? sniffKind(s.text) : s.kind;
    return { id: s.id, text: s.text, want: s.kind, kind: kind, mode: kind === "x3d" ? "x3d" : "prose", normalizer: s.normalizer || null, lx: null, idx: null };
  }
  function lexed(src) { return src.lx || (src.lx = lex(src.text, src.mode, src.normalizer)); }
  function sameRun(hay, at, needle) {
    if (at + needle.length > hay.length) return false;
    for (var j = 0; j < needle.length; j++) if (hay[at + j] !== needle[j]) return false;
    return true;
  }
  function occurrences(src, needle) {   // start token indices of non-overlapping runs, left to right
    var out = [], nxt = 0, lx = lexed(src), list, i;
    if (!needle.length) return out;
    if (!src.idx) {
      src.idx = new Map();
      lx.norms.forEach(function (w, k) { var a = src.idx.get(w); if (a) a.push(k); else src.idx.set(w, [k]); });
    }
    list = src.idx.get(needle[0]) || [];
    for (i = 0; i < list.length; i++) {
      if (list[i] < nxt || !sameRun(lx.norms, list[i], needle)) continue;
      out.push(list[i]); nxt = list[i] + needle.length;
    }
    return out;
  }
  function cpOffset(text, off) {   // UTF-16 offset -> code point offset
    var n = off, i;
    if (!/[\ud800-\udbff]/.test(text)) return off;
    for (i = 0; i < off; i++) {
      var c = text.charCodeAt(i), d = text.charCodeAt(i + 1);
      if (c >= 0xd800 && c <= 0xdbff && d >= 0xdc00 && d <= 0xdfff) { n--; i++; }
    }
    return n;
  }
  function spanOf(src, at, n, utf16) {
    var lx = lexed(src), a = lx.starts[at], b = lx.ends[at + n - 1];
    return utf16 ? [a, b] : [cpOffset(src.text, a), cpOffset(src.text, b)];
  }
  var lastSrc = null;   // findAll is called again and again on one text: lex it once
  function findAll(text, kind, quote, utf16) {
    if (!lastSrc || lastSrc.text !== text || lastSrc.want !== kind) lastSrc = makeSource({ id: "s", text: text, kind: kind });
    var src = lastSrc, q = lex(quote, src.mode, null);
    return occurrences(src, q.norms).map(function (at) { return spanOf(src, at, q.norms.length, utf16); });
  }

  // ---- tables ----------------------------------------------------------------------------------------------------------
  var NUMWORDS = table({ zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
    eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
    twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90, hundred: 100, half: 0.5, dozen: 12 });
  var UNITS = table({});   // unit word -> [category, factor to metre or second]
  [["length", 1, "m meter meters metre metres"], ["length", 0.01, "cm centimeter centimeters centimetre centimetres"],
    ["length", 0.001, "mm millimeter millimeters millimetre millimetres"], ["length", 1000, "km kilometer kilometers kilometre kilometres"],
    ["length", 0.3048, "ft foot feet"], ["length", 0.0254, "in inch inches"], ["length", 0.9144, "yd yard yards"],
    ["length", 1609.344, "mi mile miles"], ["time", 1, "s sec secs second seconds"], ["time", 0.001, "ms millisecond milliseconds"],
    ["time", 60, "min mins minute minutes"], ["time", 3600, "h hr hrs hour hours"]]
    .forEach(function (g) { g[2].split(" ").forEach(function (u) { UNITS[u] = [g[0], g[1]]; }); });
  var COLORS = table({ red: [1, 0, 0], green: [0, 1, 0], blue: [0, 0, 1], yellow: [1, 1, 0], cyan: [0, 1, 1], magenta: [1, 0, 1],
    white: [1, 1, 1], black: [0, 0, 0], orange: [1, 0.647, 0], purple: [0.5, 0, 0.5], pink: [1, 0.753, 0.796],
    brown: [0.647, 0.165, 0.165], gray: [0.5, 0.5, 0.5], grey: [0.5, 0.5, 0.5], gold: [1, 0.843, 0], silver: [0.753, 0.753, 0.753],
    teal: [0, 0.5, 0.5], navy: [0, 0, 0.5], lime: [0, 1, 0], maroon: [0.5, 0, 0], olive: [0.5, 0.5, 0], violet: [0.933, 0.51, 0.933],
    indigo: [0.294, 0, 0.51], turquoise: [0.251, 0.878, 0.816], beige: [0.961, 0.961, 0.863], crimson: [0.863, 0.078, 0.235] });
  var AXES = table({ x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1], vertical: [0, 1, 0], up: [0, 1, 0] });
  var FIELD_SEM = table({});
  [["rotation", "rotation orientation"], ["angle", "angle startAngle endAngle"],
    ["color", "diffuseColor emissiveColor specularColor color skyColor groundColor backColor"],
    ["fraction", "transparency intensity ambientIntensity shininess"], ["time", "cycleInterval startTime stopTime duration"],
    ["length", "radius height size translation bottomRadius"], ["identifier", "DEF USE name containerField"]]
    .forEach(function (g) { g[1].split(" ").forEach(function (a) { FIELD_SEM[a] = g[0]; }); });
  function fieldSemantics(name, hint) {
    if (hint) return hint;
    var tail = String(name || "").split(/[.@/\[\]]/).filter(Boolean).pop() || "";
    return FIELD_SEM[tail] || null;
  }

  // ---- numbers: Python float(), Decimal() decimals, round() and repr() -----------------------------------------------
  var NUMSTR = new RegExp("^[+-]?(?:" + D + "+\\.?" + D + "*|\\." + D + "+)(?:[eE][+-]?" + D + "+)?$", "u");
  var THOUSANDS = /^[1-9]\p{Nd}{0,2}(?:(?:\.\p{Nd}{3})+|(?:,\p{Nd}{3})+)$/u;
  function pyFloat(s) {   // NaN where Python raises ValueError
    s = toAscii(strip(s));
    return /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(s) ? Number(s) : NaN;
  }
  function decimals(x) {   // printed decimals, read from the text of the number as Decimal does
    var s, m;
    if (typeof x === "string") s = toAscii(strip(x));
    else if (typeof x === "number" && isFinite(x) && x !== Math.trunc(x)) s = String(x);
    else return 0;
    m = /^[+-]?(\d*)\.?(\d*)(?:[eE]([+-]?\d+))?$/.exec(s);
    if (!m || (m[1] === "" && m[2] === "")) return 0;
    return Math.max(0, m[2].length - (m[3] ? parseInt(m[3], 10) : 0));
  }
  function pyRound(x, n) {   // round(x, n): the exact binary value, ties to even (toFixed breaks ties upward)
    if (!isFinite(x) || n > 99) return x;
    var a = Math.abs(x), s = a.toFixed(n), t = a, i, lo;
    for (i = 0; i <= n; i++) t *= 2;   // a * 2^(n+1), exact; an odd integer means an exact tie
    if (Number.isInteger(t) && t % 2 === 1) {
      lo = a.toFixed(n + 1).slice(0, -1);
      if ((lo.charCodeAt(lo.length - 1) - 48) % 2 === 0) s = lo;
    }
    return (x < 0 || Object.is(x, -0) ? -1 : 1) * Number(s);
  }
  function thr(k) { return Number("1e-" + k); }   // 10 ** -k (Math.pow is not exact in V8)
  function pyRepr(x) {   // repr(float)
    if (!isFinite(x)) return x !== x ? "nan" : x < 0 ? "-inf" : "inf";
    if (x === 0) return Object.is(x, -0) ? "-0.0" : "0.0";
    var m = /^(-?)(\d)(?:\.(\d+))?e([+-]\d+)$/.exec(x.toExponential()), dg = m[2] + (m[3] || ""), ex = parseInt(m[4], 10), pt = ex + 1;
    if (pt > 16 || pt < -3) return m[1] + dg.charAt(0) + (dg.length > 1 ? "." + dg.slice(1) : "") + "e" + (ex < 0 ? "-" : "+") + (Math.abs(ex) < 10 ? "0" : "") + Math.abs(ex);
    if (pt <= 0) return m[1] + "0." + "0".repeat(-pt) + dg;
    return m[1] + (dg.length <= pt ? dg + "0".repeat(pt - dg.length) + ".0" : dg.slice(0, pt) + "." + dg.slice(pt));
  }
  function uniq(a) { return Array.from(new Set(a)).sort(); }
  function cmp(state, derivation, note) { return { state: state || "unchecked", derivation: derivation || [], note: note || "" }; }

  // ---- numbers read from a quote -------------------------------------------------------------------------------------------
  // a detached minus ("Discount (5%) - EUR 1,014.50") is not a range or a subtraction ("10 - 12 m"): a digit just before the dash joins two numbers
  var DETACHED = new RegExp("(?:^|(?<=[^" + D + S + "])[" + S + "]|^[" + S + "]*)[-\\u2212\\u2013][" + S + "]+(?:[^" + S + "]+[" + S + "]+){0,2}$", "u");
  function lastCps(text, end, n) {   // the n code points before UTF-16 offset `end` (Python slices code points)
    var k = end, c = 0;
    while (k > 0 && c < n) { k--; if (k > 0 && /[\udc00-\udfff]/.test(text.charAt(k)) && /[\ud800-\udbff]/.test(text.charAt(k - 1))) k--; c++; }
    return text.slice(k, end);
  }
  function readings(raw) {   // every way a prose number can be read: 3.000 is 3 and 3000; 1.234,50 is 1234.5
    var s = raw.replace(/['\u2019]/g, ""), sign = s.charAt(0) === "-" ? -1 : 1, exp = "", m, cands = new Set(), out = [];
    s = s.replace(/^[+-]+/, "");
    if ((m = /^(.*?)[eE]([+-]?\p{Nd}+)$/u.exec(s))) { s = m[1]; exp = "e" + m[2]; }
    var hasC = s.indexOf(",") >= 0, hasP = s.indexOf(".") >= 0;
    function count(c) { return s.split(c).length - 1; }
    if (!hasC && !hasP) cands.add(s);
    else if (hasC !== hasP && (THOUSANDS.test(s) || count(hasC ? "," : ".") > 1)) cands.add(s.replace(/[,.]/g, ""));
    if (hasC && hasP) {
      var dec = s.lastIndexOf(",") > s.lastIndexOf(".") ? "," : ".", grp = dec === "," ? "." : ",";
      cands.add(s.split(grp).join("").split(dec).join("."));
    } else [",", "."].forEach(function (sep) { if (count(sep) === 1) cands.add(s.split(sep).join(".")); });
    Array.from(cands).sort().forEach(function (c) {
      var v = pyFloat(c + exp);
      if (!isNaN(v)) out.push([sign * v, decimals(c)]);
    });
    return out;
  }
  function quoteNumbers(q, rq, pol) {
    var out = [], i, n, after;
    function add(v, dp, idx, raw, aft, word) { out.push({ value: v, dp: dp, idx: idx, raw: raw, after: aft, word: !!word }); }
    for (i = 0; i < q.norms.length; i++) {
      n = q.norms[i]; after = rq.slice(q.ends[i], q.ends[i] + 16);
      if (q.kinds[i] === "n") {
        if (q.mode === "x3d") {
          var f = pyFloat(n);
          if (!isNaN(f)) add(f, decimals(n), i, n, after);
        } else {
          var detached = DETACHED.test(lastCps(rq, q.starts[i], 200));
          readings(n).forEach(function (r) {
            add(r[0], r[1], i, n, after);
            if (detached && r[0] > 0) add(-r[0], r[1], i, n, after);
          });
        }
      } else if (NUMWORDS[n] !== undefined && allows(pol, "numword")) add(NUMWORDS[n], 0, i, n, after, true);
    }
    if (q.mode === "prose") {   // thousands grouped by spaces: "1 234", "1 234 567", "1 234,50" (space, NBSP, narrow NBSP, thin space, figure space)
      var GROUP_SEP = " \xa0" + String.fromCharCode(0x202f, 0x2009, 0x2007), nn = q.norms.length, j, digits, tail, g;
      var isSep = function (s) { return s.length === 1 && GROUP_SEP.indexOf(s) >= 0; };
      for (i = 0; i < nn - 1; i++) {
        if (q.kinds[i] !== "n" || !/^[1-9]\p{Nd}{0,2}$/u.test(q.norms[i])) continue;
        j = i; digits = q.norms[i]; tail = "";
        while (j + 1 < nn && q.kinds[j + 1] === "n" && isSep(rq.slice(q.ends[j], q.starts[j + 1]))) {
          g = /^(\p{Nd}{3})(?:[.,](\p{Nd}+))?$/u.exec(q.norms[j + 1]);
          if (!g) break;
          digits += g[1]; j++;
          if (g[2] !== undefined) { tail = "." + g[2]; break; }
        }
        if (j > i) add(pyFloat(digits + tail), tail ? Array.from(tail).length - 1 : 0, i, digits + tail, rq.slice(q.ends[j], q.ends[j] + 16));
      }
    }
    return out;
  }

  // ---- unit evidence and scalar comparison --------------------------------------------------------------------------------
  var AFTER = "^[" + S + "]*";
  var RE_DEG = new RegExp(AFTER + "(?:\\u00b0|\\u00ba|degs?" + NOTW + "|degrees?" + NOTW + ")", "iu");
  var RE_RAD = new RegExp(AFTER + "(?:rads?" + NOTW + "|rad[i\\u0131\\u0130]ans?" + NOTW + ")", "iu");
  var RE_PCT = new RegExp(AFTER + "(?:%|percent" + NOTW + "|per cent" + NOTW + "|pct" + NOTW + ")", "iu");
  var RE_UNITW = new RegExp(AFTER + "([A-Za-z]+)", "u");
  var DOTI = "[i\\u0131\\u0130]";   // Python's re.I also reads i as the dotless and the dotted capital I
  // "2 in front of", "3 in the middle": "in" is a unit only before the end, a non-letter, or a word that goes with a length
  var RE_IN_UNIT = new RegExp(AFTER + "(?:$|[^" + S + "A-Za-z\\u0131\\u0130]|(?:w" + DOTI + "de|long|tall|h" + DOTI + "gh|deep|th" + DOTI + "ck|across|d" +
    DOTI + "ameter|rad" + DOTI + "us|square|cube|by|x)" + NOTW + ")", "iu");
  function evidence(qn) {
    var a = qn.after, m, w;
    if (RE_DEG.test(a)) return ["deg", null];
    if (RE_RAD.test(a)) return ["rad", null];
    if (RE_PCT.test(a)) return ["pct", null];
    m = RE_UNITW.exec(a);
    if (m && UNITS[m[1].toLowerCase()]) {
      w = m[1].toLowerCase();
      if (w === "in" && !RE_IN_UNIT.test(a.slice(m[0].length))) return [null, null];
      return ["unit", w];
    }
    return [null, null];
  }
  function eq(a, dpa, b, dpb, pol) {   // "exact" | "near" | null; a is the claimed value, b a number read from the quote
    if (Math.abs(a - b) < pol.number_tolerance) return "exact";
    if (pol.round_to_printed) {
      if (dpa > dpb && dpb >= 1 && Math.abs(pyRound(a, dpb) - b) <= thr(dpb + 3)) return b === 0 ? "near" : "exact";   // a printed zero never supports a non-zero value
      if (0 < dpa && dpa < dpb && Math.abs(pyRound(b, dpa) - a) <= thr(dpa + 3)) return "near";
    }
    return null;
  }
  function derivedEq(a, dpa, t, pol, slack) {
    if (dpa === 0) return Math.abs(a - t) < Math.max(pol.number_tolerance, 1e-9 * Math.max(1, Math.abs(t)), slack || 0);
    return Math.abs(pyRound(t, dpa) - a) <= thr(dpa + 3);
  }
  function cmpScalar(x, dpx, qns, pol, sem, angle) {
    var bestConv = null, near = null, conflict = null, i, q, ev, r, u, scale, t;
    for (i = 0; i < qns.length; i++) {
      q = qns[i]; ev = evidence(q); r = eq(x, dpx, q.value, q.dp, pol);
      if (r) {
        if (angle && ev[0] === "deg" && allows(pol, "deg2rad")) conflict = conflict || cmp("mismatch", [], "degrees written where radians are expected");
        else if (ev[0] === "pct" && sem === "fraction" && Math.abs(x) > 1 && allows(pol, "percent"))
          conflict = conflict || cmp("mismatch", [], "percent written where a 0..1 fraction is expected");
        else if (ev[0] === "unit" && (sem === "length" || sem === "time") && allows(pol, "unit")) {
          u = UNITS[ev[1]]; scale = u[0] === "length" ? u[1] / pol.length_scale : u[1];
          if (u[0] === sem && Math.abs(scale - 1) > 1e-9) conflict = conflict || cmp("mismatch", [], "unit " + ev[1] + " differs from the scene unit");
          else if (r === "exact") return cmp("match", q.word ? ["numword"] : []);
          else near = near || cmp("near");
        } else if (r === "exact") return cmp("match", q.word ? ["numword"] : []);
        else near = near || cmp("near");
      }
      if (ev[0] === "deg" && allows(pol, "deg2rad") && derivedEq(x, dpx, q.value * Math.PI / 180, pol)) bestConv = bestConv || cmp("match", ["deg2rad"]);
      else if (ev[0] === "rad" && allows(pol, "rad2deg") &&
               derivedEq(x, dpx, q.value * 180 / Math.PI, pol, q.dp >= 3 ? 0.5 * thr(q.dp) * 180 / Math.PI * 1.001 : 0)) bestConv = bestConv || cmp("match", ["rad2deg"]);
      else if (ev[0] === "pct" && allows(pol, "percent") && derivedEq(x, dpx, q.value / 100, pol)) bestConv = bestConv || cmp("match", ["percent"]);
      else if (ev[0] === "unit" && allows(pol, "unit")) {
        u = UNITS[ev[1]]; t = u[0] === "length" ? q.value * u[1] / pol.length_scale : q.value * u[1];
        if (Math.abs(t - q.value) > 1e-12 && derivedEq(x, dpx, t, pol)) bestConv = bestConv || cmp("match", ["unit:" + ev[1]]);
      }
    }
    return bestConv || near || conflict || cmp("mismatch");
  }

  // ---- vectors and colours --------------------------------------------------------------------------------------------------
  function floats(v) {   // numbers of a vector-like value (array, or "1 2 3" / "1,2,3"); null when it is not one
    if (Array.isArray(v)) {   // numbers, or numbers written as text
      return v.every(function (x) { return typeof x === "number" || (typeof x === "string" && NUMSTR.test(strip(x))); })
        ? v.map(function (x) { return typeof x === "number" ? x : pyFloat(x); }) : null;
    }
    if (typeof v !== "string") return null;
    var parts = strip(v).split(RE_SPLIT).filter(function (p) { return p !== ""; });
    return parts.length >= 2 && parts.every(function (p) { return NUMSTR.test(p); }) ? parts.map(pyFloat) : null;
  }
  function valueDecimals(v) {
    return typeof v === "string" ? strip(v).split(RE_SPLIT).filter(function (p) { return p !== ""; }).map(decimals) : v.map(decimals);
  }
  function hue(r, g, b, mx, d) {
    var h = mx === r ? (g - b) / d : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    if (mx === r) { h = h % 6; if (h < 0) h += 6; }   // Python's % takes the sign of the divisor
    return h * 60;
  }
  function hueClass(rgb, name) {
    var r = rgb[0], g = rgb[1], b = rgb[2], mx = Math.max(r, g, b), mn = Math.min(r, g, b), s = mx === 0 ? 0 : (mx - mn) / mx;
    if (name === "white") return mx >= 0.85 && s <= 0.15;
    if (name === "black") return mx <= 0.15;
    if (name === "gray" || name === "grey" || name === "silver") return s <= 0.15 && mx >= 0.25 && mx <= 0.85;
    if (s < 0.35 || mx < 0.25) return false;
    var c = COLORS[name], cm = Math.max(c[0], c[1], c[2]), cd = cm - Math.min(c[0], c[1], c[2]);
    if (cd === 0) return false;
    var dh = Math.abs(hue(r, g, b, mx, mx - mn) - hue(c[0], c[1], c[2], cm, cd));
    return Math.min(dh, 360 - dh) <= 30;
  }
  var RE_HEX = new RegExp("(?<![" + W + "])#?([0-9a-fA-F]{6})(?![" + W + "])", "gu");
  function cmpColor(comps, qraw, q, pol) {
    var i, m, best = null, near = function (a, b) { return a.every(function (x, k) { return Math.abs(x - b[k]) <= 0.05; }); };
    if (comps.length !== 3 || !comps.every(function (c) { return c >= -1e-9 && c <= 1 + 1e-9; })) return cmp("mismatch");
    if (allows(pol, "hex")) {
      RE_HEX.lastIndex = 0;
      while ((m = RE_HEX.exec(qraw)) !== null) {
        if (m[0].charAt(0) !== "#" && !(/[0-9]/.test(m[1]) && /[a-fA-F]/.test(m[1]))) continue;   // "123456" is a number and "facade" a word
        var rgb = [0, 2, 4].map(function (k) { return parseInt(m[1].substr(k, 2), 16) / 255; });
        if (comps.every(function (c, k) { return Math.abs(c - rgb[k]) <= 0.5 / 255 + 1e-9; })) return cmp("match", ["hex"]);
      }
    }
    if (allows(pol, "rgb255")) {
      var ints = quoteNumbers(q, qraw, pol).filter(function (n) { return !n.word && isFinite(n.value) && n.value === Math.trunc(n.value) && n.value >= 0 && n.value <= 255; });
      if (ints.length >= 3 && Math.max.apply(null, ints.map(function (n) { return n.value; })) > 1) {
        for (i = 0; i < ints.length - 2; i++)
          if (comps.every(function (c, k) { return Math.abs(c * 255 - ints[i + k].value) <= 0.5 + 1e-9; })) return cmp("match", ["rgb255"]);
      }
    }
    if (allows(pol, "colorname")) {
      for (i = 0; i < q.norms.length; i++) {
        var n = q.norms[i];
        if (!COLORS[n]) continue;
        if (near(comps, COLORS[n])) return cmp("match", ["colorname:" + n]);
        if (hueClass(comps, n)) best = best || cmp("near", ["colorname-class:" + n]);
      }
      if (best) return best;
    }
    return cmp("mismatch");
  }
  function cmpVector(comps, dps, qraw, q, pol, sem) {
    var qns = quoteNumbers(q, qraw, pol), k = comps.length, usem = sem === "length" || sem === "time" ? sem : null, note = "", r, i;
    var ranks = Array.from(new Set(qns.map(function (n) { return n.idx; }))).sort(function (a, b) { return a - b; });
    var byRank = ranks.map(function (ix) { return qns.filter(function (n) { return n.idx === ix; }); });   // the readings of each number token
    function run(seq) {   // seq = [[component index, value, decimals]] must sit on CONSECUTIVE numbers of the quote; unit conflicts count per component
      var s0, off, j, hit, res, derivs, near, ok, angle;
      for (s0 = 0; s0 + seq.length <= byRank.length; s0++) {
        derivs = []; near = false; ok = true;
        for (off = 0; off < seq.length && ok; off++) {
          angle = sem === "rotation" && k === 4 && seq[off][0] === 3;   // degrees written for radians is caught on every path
          hit = null;
          for (j = 0; j < byRank[s0 + off].length && !hit; j++) {
            res = cmpScalar(seq[off][1], seq[off][2], [byRank[s0 + off][j]], pol, usem, angle);
            if (res.state === "match" || res.state === "near") hit = res; else note = note || res.note;
          }
          if (!hit) ok = false;
          else { derivs = derivs.concat(hit.derivation); near = near || hit.state === "near"; }
        }
        if (ok) return { near: near, derivs: derivs };
      }
      return null;
    }
    var full = run(comps.map(function (c, ci) { return [ci, c, dps[ci]]; }));   // 1. every component, in order, on consecutive numbers
    if (full) return cmp(full.near ? "near" : "match", uniq(full.derivs));
    var nz = [], part;   // 1b. only the non-zero components, and only when the quote does not state every component
    comps.forEach(function (c, ci) { if (Math.abs(c) > 1e-12) nz.push([ci, c, dps[ci]]); });
    if (nz.length > 0 && nz.length < k && sem !== "color" && byRank.length < k && (part = run(nz)))
      return cmp("near", uniq(["zero-fill"].concat(part.derivs)), "components the quote does not mention are zero");
    if (sem === "color" && k === 3) { r = cmpColor(comps, qraw, q, pol); if (r.state !== "mismatch") return r; }   // 2. hex, 0-255, names
    if (sem === "rotation" && k === 4 && allows(pol, "axis")) {   // 3. an axis word and one angle: (-axis, -angle) is the same turn, (-axis, +angle) is not
      var words = q.norms.filter(function (n, ci) { return q.kinds[ci] === "w" && AXES[n]; });
      var angs = qns.filter(function (n) { return !n.word; });
      if (words.length && angs.length) {
        var ax = AXES[words[0]], head = comps.slice(0, 3);
        var same = head.every(function (a, ci) { return Math.abs(a - ax[ci]) < 1e-6; });
        var flip = head.every(function (a, ci) { return Math.abs(a + ax[ci]) < 1e-6; });
        if (same || flip) {
          for (i = 0; i < angs.length; i++) {
            r = cmpScalar(flip ? -comps[3] : comps[3], dps[3], [angs[i]], pol, null, true);
            if (r.state === "match" || r.state === "near") return cmp(r.state, uniq(["axis:" + words[0]].concat(r.derivation)));
            note = note || r.note;
          }
        }
      }
    }
    if (allows(pol, "broadcast") && k >= 2 && new Set(comps).size === 1) {   // 4. one number repeated
      r = cmpScalar(comps[0], dps[0], qns, pol, usem, false);
      if (r.state === "match" || r.state === "near") return cmp(r.state, uniq(["broadcast"].concat(r.derivation)));
      note = note || r.note;
    }
    if (sem === "color" && k === 3 && allows(pol, "colorname") && q.norms.some(function (n) { return COLORS[n]; }))
      return cmp("mismatch", [], note || "the colour named in the quote is another colour");
    return qns.length ? cmp("mismatch", [], note) : cmp("unchecked");
  }

  // ---- text, identifiers, dates -------------------------------------------------------------------------------------------
  var MONTHS = table({ jan: 1, january: 1, feb: 2, february: 2, mar: 3, march: 3, apr: 4, april: 4, may: 5, jun: 6, june: 6, jul: 7, july: 7,
    aug: 8, august: 8, sep: 9, sept: 9, september: 9, oct: 10, october: 10, nov: 11, november: 11, dec: 12, december: 12 });
  var RE_DATE_NUM = new RegExp("^" + D + "+(?:[./'\\u2019,]" + D + "+)*$", "u");
  function dateParts(s) {   // 3 numbers that could be a date, or null
    var parts = s.match(/\p{Nd}+/gu) || [], n, y, o;
    if (parts.length !== 3 || !new RegExp("^[\\p{Nd}" + S + "./-]+$", "u").test(strip(s))) return null;
    n = parts.map(function (p) { return parseInt(toAscii(p), 10); });
    if (/^\p{Nd}+\.\p{Nd}+\.\p{Nd}+$/u.test(strip(s)) && !n.some(function (v) { return v >= 1000 && v <= 2999; })) return null;   // a dotted triple without a four-digit year is a version
    for (y = 0; y < 3; y++) {
      o = n.filter(function (v, i) { return i !== y; });
      if ((n[y] >= 1000 && n[y] <= 2999 || n[y] < 100) && o[0] >= 1 && o[0] <= 31 && o[1] >= 1 && o[1] <= 31 && Math.min(o[0], o[1]) <= 12) return n;
    }
    return null;
  }
  function cmpDate(parts, q) {   // every part of the date is held by a DIFFERENT number or month name of the quote, within 6 tokens
    var vals = [], i;
    q.norms.forEach(function (n, ix) {
      if (q.kinds[ix] === "n" && RE_DATE_NUM.test(n))
        n.match(/\p{Nd}+/gu).forEach(function (g) { var v = parseInt(toAscii(g), 10); vals.push(v < 100 ? [v, v + 2000] : [v]); });
      else if (q.kinds[ix] === "w" && MONTHS[n] !== undefined) vals.push([MONTHS[n]]);
      else vals.push([]);
    });
    function assign(todo, win, used) {
      return !todo.length || win.some(function (s, j) { return used.indexOf(j) < 0 && s.indexOf(todo[0]) >= 0 && assign(todo.slice(1), win, used.concat([j])); });
    }
    for (i = 0; i < vals.length; i++) if (assign(parts, vals.slice(i, i + 6), [])) return cmp("match", ["date"]);
    return cmp("mismatch");
  }
  function contains(hay, needle) {
    for (var i = 0; i + needle.length <= hay.length; i++) if (needle.length && sameRun(hay, i, needle)) return true;
    return false;
  }
  function spells(words, squeezed) {   // do consecutive words join into the digits/letters of `squeezed`?
    var start, j, joined;
    if (Array.from(squeezed).length < 4) return false;
    for (start = 0; start < words.length; start++) {
      joined = "";
      for (j = start; j < words.length; j++) {
        joined += words[j];
        if (joined === squeezed) return true;
        if (squeezed.indexOf(joined) !== 0) break;
      }
    }
    return false;
  }
  function isIdentifier(t) { return /^[A-Za-z_][\p{L}\p{N}_.-]*$/u.test(t); }

  function compare(value, quote, q, pol, sem) {
    var comps, num = null, r, text, wanted, s, cps, parts;
    if (value === null || value === undefined || typeof value === "boolean" || (typeof value === "object" && !Array.isArray(value))) return cmp("unchecked");
    comps = floats(value);
    if (comps !== null && comps.length >= 2) {
      if (comps.length > 64) {   // long arrays: only a verbatim (numeric, consecutive) copy of the attribute text counts
        var vals = q.norms.map(function (n, ix) { var f = q.kinds[ix] === "n" ? pyFloat(n) : NaN; return isNaN(f) ? null : f; });
        return contains(vals, comps) ? cmp("match", ["verbatim"]) : cmp("mismatch");
      }
      return cmpVector(comps, valueDecimals(value), quote, q, pol, sem);
    }
    if (Array.isArray(value)) return cmp("unchecked");
    if (typeof value === "number") num = value;
    else if (typeof value === "string" && NUMSTR.test(strip(value))) {
      s = strip(value); cps = Array.from(s);
      if (!(cps.length > 1 && cps[0] === "0" && /^\p{Nd}$/u.test(cps[1])) && sem !== "identifier") num = pyFloat(s);
    }
    if (num !== null) {
      if (!isFinite(num)) return cmp("mismatch");
      r = cmpScalar(num, decimals(value), quoteNumbers(q, quote, pol), pol, sem === "length" || sem === "time" || sem === "fraction" ? sem : null,
        sem === "angle" || sem === "rotation");
      if (r.state === "mismatch" && typeof value === "string" && q.mode === "prose" && pol.match_reformatted_identifiers &&
          spells(q.norms, value.replace(/\P{Nd}/gu, ""))) return cmp("match", ["reformatted"]);
      return r;
    }
    text = String(value);
    parts = dateParts(text);
    if (parts !== null) return cmpDate(parts, q);
    wanted = lex(text, q.mode, null).norms;
    if (!wanted.length) return cmp("unchecked");
    if (contains(q.norms, wanted)) return cmp("match");
    if (q.mode === "prose" && pol.match_reformatted_identifiers && spells(q.norms, wanted.join(""))) return cmp("match", ["reformatted"]);
    if (pol.code_values_unchecked && /^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$/.test(text)) return cmp("unchecked");
    return cmp("mismatch");
  }

  function verdictOf(status, vstate, value, quoteWords, pol, occurrences, identifier, disambiguated) {
    if (status === "no_text_layer" || status === "no_quote") return "unchecked";
    if ((status !== "found" && status !== "moved") || quoteWords < pol.min_quote_words) return "check";
    if (status === "moved" && pol.moved_is_check) return "check";
    if (vstate === "match") return pol.ambiguous_quote_is_check && (occurrences === undefined ? 1 : occurrences) > 1 && !disambiguated ? "check" : "verified";
    if (vstate === "near") return pol.reworded_is_problem ? "check" : "reworded";
    if (vstate === "mismatch") {
      var numeric = typeof value === "number" || floats(value) !== null ||
        (typeof value === "string" && (NUMSTR.test(strip(value)) || dateParts(value) !== null || /^\p{Nd}+(?:\.\p{Nd}+){2,}$/u.test(strip(value))));
      return !numeric && !identifier ? (pol.reworded_is_problem ? "check" : "reworded") : "check";
    }
    return "unchecked";
  }

  // ---- check: FIND, choose, COMPARE, verdict ---------------------------------------------------------------------------
  function sliceEq(a, b) { return a.length === b.length && a.every(function (x, i) { return x === b[i]; }); }
  function choose(src, occ, qNorms, claim) {   // pick one of several occurrences from prefix / suffix / line hints
    if (occ.length === 1) return [occ[0], ""];
    var lx = lexed(src), cands = occ.slice(), how = "", n = qNorms.length, pre, suf, keep, on;
    if (claim.prefix) {
      pre = lex(claim.prefix, src.mode, src.normalizer).norms;
      keep = cands.filter(function (i) { return sliceEq(lx.norms.slice(Math.max(0, i - pre.length), i), pre); });
      if (keep.length) { cands = keep; how = "prefix"; }
    }
    if (claim.suffix && cands.length > 1) {
      suf = lex(claim.suffix, src.mode, src.normalizer).norms;
      keep = cands.filter(function (i) { return sliceEq(lx.norms.slice(i + n, i + n + suf.length), suf); });
      if (keep.length) { cands = keep; how = how ? how + "+suffix" : "suffix"; }
    }
    // a field / path hint would need the parsed scene (SceneIndex): not ported
    if (Number.isInteger(claim.line) && claim.line > 0 && cands.length > 1) {   // only a candidate that sits exactly on that line
      on = cands.filter(function (i) { return src.text.slice(0, lx.starts[i]).split("\n").length === claim.line; });
      if (on.length) {
        cands = on.length === 1 ? on.slice(0, 1) : on;
        if (on.length === 1) how = how ? how + "+line" : "line";
      }
    }
    return [cands[0], cands.length === 1 ? how : ""];
  }
  function pyReprStr(s) {   // repr(str)
    var qt = s.indexOf("'") >= 0 && s.indexOf('"') < 0 ? '"' : "'", hex = function (cp, w) { return ("00000000" + cp.toString(16)).slice(-w); };
    return qt + Array.from(s).map(function (ch) {
      var cp = ch.codePointAt(0);
      if (ch === qt || ch === "\\") return "\\" + ch;
      if (ch === "\n") return "\\n";
      if (ch === "\r") return "\\r";
      if (ch === "\t") return "\\t";
      if (ch !== " " && /[\p{C}\p{Z}]/u.test(ch)) return cp < 0x100 ? "\\x" + hex(cp, 2) : cp < 0x10000 ? "\\u" + hex(cp, 4) : "\\U" + hex(cp, 8);
      return ch;
    }).join("") + qt;
  }
  function checkOne(claim, srcs, pol) {
    var sem = fieldSemantics(claim.field, claim.ftype), rawQuote = claim.quote, byId = new Map(), pref = null, unknown, i, found = null, s, q, occ;
    if (rawQuote && typeof rawQuote !== "string") throw new TypeError("the quote is not text");
    var quote = rawQuote || "", cited = claim.source !== undefined && claim.source !== null;
    srcs.forEach(function (x, k) { byId.set(x.id, k); });
    if (cited && byId.has(claim.source)) pref = byId.get(claim.source);
    unknown = cited && pref === null;   // the writer cited a source that does not exist
    if (pref === null) pref = claim.document >= 1 && claim.document <= srcs.length ? claim.document - 1 : 0;
    var it = { field: claim.field, value: claim.value, quote: quote, source: srcs.length ? srcs[pref].id : "", document: pref + 1,
      status: "not_found", value_status: "unchecked", verdict: "unchecked", span: null, span16: null, occurrences: 0,
      derivation: [], note: "", disambiguated_by: "" };
    if (!strip(quote)) { it.status = "no_quote"; return it; }
    if (!srcs.some(function (x) { return x.kind !== "binary"; })) { it.status = "no_text_layer"; return it; }   // nothing with a text layer to look in
    var order = [pref];
    srcs.forEach(function (x, k) { if (k !== pref) order.push(k); });
    for (i = 0; i < order.length && !found; i++) {
      s = srcs[order[i]];
      if (s.kind === "binary") continue;
      q = lex(quote, s.mode, s.normalizer); occ = occurrences(s, q.norms);
      if (occ.length) found = { i: order[i], s: s, q: q, occ: occ };
    }
    if (!found) { it.verdict = "check"; return it; }
    s = found.s; q = found.q; occ = found.occ;
    var ch = choose(s, occ, q.norms, claim), at = ch[0], how = ch[1], n = q.norms.length;
    it.document = found.i + 1; it.source = s.id;
    it.status = found.i === pref && !unknown ? "found" : "moved";
    it.occurrences = occ.length;
    it.span = spanOf(s, at, n, false); it.span16 = spanOf(s, at, n, true);
    it.disambiguated_by = how;
    var c = compare(claim.value, quote, q, pol, sem);
    if (c.state === "mismatch" && typeof claim.value === "string" && !NUMSTR.test(strip(claim.value))) {   // a long text value that runs through the quote
      var want = lex(claim.value, s.mode, s.normalizer).norms;
      if (want.length > n) {
        occurrences(s, want).some(function (j) {
          if (j < at + n && at < j + want.length) { c = cmp("match", ["value-extends-quote"]); return true; }
          return false;
        });
      }
    }
    it.value_status = c.state; it.derivation = c.derivation; it.note = c.note;
    if (unknown) it.note = "the cited source " + (typeof claim.source === "string" ? pyReprStr(claim.source) : String(claim.source)) + " is not among the sources. " + it.note;
    var ident = sem === "identifier" || (s.kind === "x3d" && typeof claim.value === "string" && isIdentifier(claim.value) && !NUMSTR.test(claim.value));
    it.verdict = verdictOf(it.status, c.state, claim.value, n, pol, occ.length, ident, !!how);
    if (it.verdict === "check" && c.state === "mismatch" && !c.note && !/\p{Nd}/u.test(quote) &&
        !(allows(pol, "numword") && q.norms.some(function (w) { return NUMWORDS[w] !== undefined; })) &&
        (typeof claim.value === "number" || floats(claim.value) !== null))
      it.verdict = "unchecked";   // a number written in words that no table read
    return it;
  }
  function check(claim, sources, policy) {
    var pol = makePolicy(policy), srcs = (Array.isArray(sources) ? sources : [sources]).map(function (s, i) {
      return makeSource(typeof s === "string" ? { id: "source-" + (i + 1), text: s } : s);
    });
    try {
      return checkOne(claim, srcs, pol);
    } catch (e) {   // a claim that cannot be read is reported as unchecked and the run goes on
      var d = claim && typeof claim === "object" ? claim : {};
      return { field: String(d.field === undefined ? "" : d.field), value: d.value, quote: String(d.quote || ""), source: srcs.length ? srcs[0].id : "",
        document: 1, status: "no_quote", value_status: "unchecked", verdict: "unchecked", span: null, span16: null, occurrences: 0, derivation: [],
        note: "claim not checked: " + ((e && e.name) || "Error") + ": " + ((e && e.message) || e), disambiguated_by: "" };
    }
  }

  return { check: check, findAll: findAll, lex: lex, Source: makeSource, occurrences: occurrences, fieldSemantics: fieldSemantics,
    compare: compare, verdictOf: verdictOf, policy: makePolicy, strictPolicy: strictPolicy, decimals: decimals, schema: "x3dtrace/0.1",
    internals: { casefold: casefold, toAscii: toAscii, pyRound: pyRound, pyRepr: pyRepr, readings: readings, unescapeEnt: unescapeEnt, pyFloat: pyFloat,
      dateParts: dateParts, hueClass: hueClass, NAMED: NAMED } };
});
