/* js-port-of-8dd0d3e -- Python-semantics helpers (X3DVAL._m.py).
 * Reproduces the observable behaviour of the Python builtins the fork's semantic.py
 * relies on: sorted() (code-point order), repr() of str, str.isspace()/isdigit()/
 * strip() (Unicode), int(), float() grammar, re.split(r"[\s,]+") token counting.
 */
(function (X3DVAL) {
  // Python str.isspace() == re `\s` for str patterns: bidi WS/B/S or category Zs.
  var PY_WS = '\\t\\n\\x0b\\x0c\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';
  var RE_WS_ONE = new RegExp('^[' + PY_WS + ']$');
  var RE_STRIP = new RegExp('^[' + PY_WS + ']+|[' + PY_WS + ']+$', 'g');
  var RE_SPLIT_TOKENS = new RegExp('[' + PY_WS + ',]+');
  // str.isdigit(): Numeric_Type=Decimal (\p{Nd}) or Numeric_Type=Digit (superscripts, circled digits, ...).
  var RE_DIGIT = /^(?:\p{Nd}|[²³¹፩-፱᧚⁰⁴-⁹₀-₉①-⑨⑴-⑼⒈-⒐⓪⓵-⓽⓿❶-❾➀-➈➊-➒]|\u{10a40}|\u{10a41}|\u{10a42}|\u{10a43}|[\u{10e60}-\u{10e68}]|[\u{11052}-\u{1105a}]|[\u{1f100}-\u{1f10a}])$/u;
  var RE_NONPRINT = /[\p{Cc}\p{Cf}\p{Cs}\p{Co}\p{Cn}\p{Zl}\p{Zp}\p{Zs}]/u;
  var RE_ASCII_DIGIT = /^[0-9]$/;

  function pyIsSpace(ch) { return RE_WS_ONE.test(ch); }
  function pyIsDigit(ch) { return RE_DIGIT.test(ch); }
  function pyStrip(s) { return s.replace(RE_STRIP, ''); }
  function pyAnyIsSpace(s) { for (var ch of s) if (RE_WS_ONE.test(ch)) return true; return false; }
  function pyFirstChar(s) { // Python s[0]: first code point
    var cp = s.codePointAt(0); return cp === undefined ? '' : String.fromCodePoint(cp);
  }

  // Compare two strings by Unicode code points (Python str ordering).
  function cmpStr(a, b) {
    var i = 0, j = 0;
    while (i < a.length && j < b.length) {
      var ca = a.codePointAt(i), cb = b.codePointAt(j);
      if (ca !== cb) return ca < cb ? -1 : 1;
      i += ca > 0xffff ? 2 : 1; j += cb > 0xffff ? 2 : 1;
    }
    if (i < a.length) return 1;
    if (j < b.length) return -1;
    return 0;
  }
  function pySorted(iterable) { return Array.from(iterable).sort(cmpStr); }
  // Python tuple comparison for arrays of str|number (used for sort keys).
  function cmpTuple(a, b) {
    var n = Math.min(a.length, b.length);
    for (var i = 0; i < n; i++) {
      var x = a[i], y = b[i];
      if (typeof x === 'string' && typeof y === 'string') { var c = cmpStr(x, y); if (c) return c; }
      else if (x !== y) return x < y ? -1 : 1;
    }
    return a.length - b.length;
  }

  function hex(n, w) { var s = n.toString(16); while (s.length < w) s = '0' + s; return s; }
  // repr(str)
  function pyRepr(s) {
    var q = "'";
    if (s.indexOf("'") >= 0 && s.indexOf('"') < 0) q = '"';
    var out = q;
    for (var ch of s) {
      var cp = ch.codePointAt(0);
      if (ch === q || ch === '\\') out += '\\' + ch;
      else if (ch === '\n') out += '\\n';
      else if (ch === '\r') out += '\\r';
      else if (ch === '\t') out += '\\t';
      else if (cp < 0x20 || cp === 0x7f) out += '\\x' + hex(cp, 2);
      else if (cp < 0x7f) out += ch;
      else if (RE_NONPRINT.test(ch)) {
        if (cp <= 0xff) out += '\\x' + hex(cp, 2);
        else if (cp <= 0xffff) out += '\\u' + hex(cp, 4);
        else out += '\\U' + hex(cp, 8);
      } else out += ch;
    }
    return out + q;
  }

  // int(s) for base 10; throws on ValueError. Unicode decimal digits are mapped via \p{Nd} offsets.
  var RE_INT = /^[+-]?\p{Nd}(?:_?\p{Nd})*$/u;
  function asciiDigits(s) {
    var out = '';
    for (var ch of s) {
      if (RE_ASCII_DIGIT.test(ch) || ch === '_' || ch === '+' || ch === '-' || ch === '.' || ch === 'e' || ch === 'E') { out += ch; continue; }
      if (/\p{Nd}/u.test(ch)) { // find digit value: scan down to the zero of its block
        var cp = ch.codePointAt(0), v = 0;
        while (v < 9 && /\p{Nd}/u.test(String.fromCodePoint(cp - v - 1))) v++;
        out += String(v);
      } else out += ch;
    }
    return out;
  }
  function pyInt(s) {
    var t = pyStrip(String(s));
    if (!RE_INT.test(t)) throw new RangeError('invalid literal for int() with base 10: ' + pyRepr(s));
    var n = Number(asciiDigits(t).replace(/_/g, ''));
    if (!Number.isFinite(n)) throw new RangeError('int overflow');
    return n;
  }

  // float(s); throws RangeError on ValueError. Accepts underscores between digits, inf/infinity/nan.
  var RE_FLOAT = /^[+-]?(?:(?:\p{Nd}(?:_?\p{Nd})*)(?:\.(?:\p{Nd}(?:_?\p{Nd})*)?)?|\.\p{Nd}(?:_?\p{Nd})*)(?:[eE][+-]?\p{Nd}(?:_?\p{Nd})*)?$/u;
  var RE_SPECIAL = /^[+-]?(inf|infinity|nan)$/i;
  function pyFloat(s) {
    var t = pyStrip(String(s));
    var m = RE_SPECIAL.exec(t);
    if (m) {
      var name = m[1].toLowerCase();
      if (name === 'nan') return NaN;
      return t[0] === '-' ? -Infinity : Infinity;
    }
    if (!RE_FLOAT.test(t)) throw new RangeError('could not convert string to float: ' + pyRepr(s));
    return Number(asciiDigits(t).replace(/_/g, ''));
  }
  // [x for x in re.split(r"[\s,]+", attr.strip()) if x]
  function tokens(attr) { return pyStrip(attr).split(RE_SPLIT_TOKENS).filter(function (x) { return x; }); }
  function countTokens(attr) { return tokens(attr).length; }
  // _floats(): all tokens as floats, or [] on any ValueError
  function pyFloats(attr) {
    try { return tokens(attr).map(pyFloat); } catch (e) { return []; }
  }
  function isFinite_(x) { return Number.isFinite(x); }

  X3DVAL._m.py = {
    PY_WS: PY_WS, pyIsSpace: pyIsSpace, pyIsDigit: pyIsDigit, pyStrip: pyStrip, pyAnyIsSpace: pyAnyIsSpace,
    pyFirstChar: pyFirstChar, cmpStr: cmpStr, cmpTuple: cmpTuple, pySorted: pySorted, pyRepr: pyRepr,
    pyInt: pyInt, pyFloat: pyFloat, pyFloats: pyFloats, tokens: tokens, countTokens: countTokens, isFinite: isFinite_
  };
})((typeof self !== 'undefined' ? self : globalThis).X3DVAL);
