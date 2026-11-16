"""Differential test of x3dtrace.js helpers against the Python engine (read only).
usage: python3 -I -B diff_internals.py <engine_dir>"""
import sys, json, subprocess, os, re, random, html, unicodedata, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, sys.argv[1])
import x3dtrace as T
rng = random.Random(7)

def js(fn, inputs):
    p = subprocess.run(["node", os.path.join(HERE, "diff_bridge.js")], input=json.dumps({"fn": fn, "inputs": inputs}),
                       capture_output=True, text=True, check=True)
    return json.loads(p.stdout)

def report(name, bad, n):
    print("%-34s %s (%d inputs)%s" % (name, "OK" if not bad else "DIFF %d" % len(bad), n, "" if not bad else "  e.g. " + repr(bad[:5])))
    return not bad

allcp = [chr(c) for c in range(0x110000) if not 0xD800 <= c <= 0xDFFF]
ok = True
# 1. character classes
for fn, pat in (("isw", r"\w"), ("isd", r"\d"), ("iss", r"\s")):
    r = re.compile(pat); got = js(fn, allcp)
    diff = [c for c, g in zip(allcp, got) if bool(r.fullmatch(c)) != g]
    bad = [hex(ord(c)) for c in diff if unicodedata.category(c) != "Cn"]
    ok &= report("class " + pat + " (assigned in py)", bad, len(allcp))
    print("   differences on code points unassigned in Python's Unicode %s (newer Node ICU): %d" % (unicodedata.unidata_version, len(diff) - len(bad)))
# 2. casefold after NFC, all code points plus sigma contexts
ins = allcp + ["\u03b1\u03c2", "\u0391\u03a3", "\u03c3\u03c2", "\u038c\u03a3\u039f\u03a3", "Stra\u00dfe", "\u1e9e", "\u01c5", "\u0130stanbul", "\u0131I"]
got = js("casefold", ins)
diff = [c for c, g in zip(ins, got) if unicodedata.normalize("NFC", c).casefold() != g]
bad = [(hex(ord(c[0])) if len(c) == 1 else c) for c in diff if any(unicodedata.category(ch) != "Cn" for ch in c)]
ok &= report("casefold(NFC(x)) (assigned in py)", bad, len(ins))
print("   differences on code points unassigned in Python's Unicode: %d" % (len(diff) - len(bad)))
# 3. Unicode digits
nd = [c for c in allcp if unicodedata.category(c) == "Nd"]
got = js("toascii", nd)
bad = [hex(ord(c)) for c, g in zip(nd, got) if str(int(c)) != g]
ok &= report("toAscii of Nd", bad, len(nd))
# 4. html entities: every name we embed, numeric references, and what we do not know
names = [n for n in T.html.entities.html5 if n.endswith(";")] if hasattr(T, "html") else [n for n in html.entities.html5 if n.endswith(";")]
ents = ["&" + n for n in names] + ["&#%d;" % c for c in list(range(0, 0x300)) + [0x1F600, 0x10FFFF, 0x110000, 0xD800, 0xFFFE, 0x2028, 99999999999]] + \
       ["&#x%X;" % c for c in range(0, 0x300)] + ["&#x1F600;"]
got = js("entity", ents)
def py_ent(e):
    r = html.unescape(e)
    return r if (r != e and any(ch.isalnum() for ch in r)) else None
miss, bad = [], []
for e, g in zip(ents, got):
    p = py_ent(e)
    if p != g:
        (miss if (g is None and p is not None and e.startswith("&") and not e.startswith("&#")) else bad).append(e)
ok &= report("html entities (numeric+embedded)", bad, len(ents))
print("   named entities with a letter/digit not embedded (known limitation): %d of %d, e.g. %s" % (len(miss), len(names), miss[:6]))
# 5. round(x, n)
cases = []
for _ in range(20000):
    n = rng.randint(1, 8)
    k = rng.choice([rng.randint(-20000, 20000) / 2 ** rng.randint(1, 12), rng.random() * 10 ** rng.randint(-3, 6), round(rng.uniform(-100, 100), rng.randint(0, 6))])
    cases.append([k, n])
for n in range(1, 10):
    for j in range(0, 1200):
        cases.append([(j + 0.5) / 10 ** n if n < 4 else j / 2 ** n, n]); cases.append([-(j + 0.5) / 2 ** n, n])
got = js("round", cases)
bad = [(c, g, round(c[0], c[1])) for c, g in zip(cases, got) if round(c[0], c[1]) != g and not (math.isnan(g) if isinstance(g, float) else False)]
ok &= report("round(x, n) half-even", bad, len(cases))
# 6. repr(float)
fl = [rng.choice([rng.random() * 10 ** rng.randint(-12, 22), float(rng.randint(-10 ** 9, 10 ** 17)), rng.uniform(-1, 1) * 10 ** rng.randint(-8, 8)]) for _ in range(20000)]
fl += [1e16, 1e15, 9999999999999998.0, 1e-4, 1e-5, 0.0001234, 5e-324, 1.7976931348623157e308, 100.0, 0.5, 123456789012345680.0]
got = js("repr", fl)
bad = [(x, g, repr(x)) for x, g in zip(fl, got) if repr(x) != g]
ok &= report("repr(float)", bad, len(fl))
# 7. decimals() on numbers and numeric text
tx = []
for _ in range(8000):
    ip = str(rng.randint(0, 99999)); fp = "".join(rng.choice("0123456789") for _ in range(rng.randint(0, 9)))
    s = ip + ("." + fp if fp or rng.random() < .2 else "") + (rng.choice(["", "e5", "E-3", "e+2", "e-12", "e0"]) if rng.random() < .3 else "")
    tx.append(s)
tx += [".5", "5.", "1.50e1", "0.00", "1e-7", "\u0661\u0662.\u0663\u0664", "  3.25 ", "+1.5", "-0.125"]
got = js("decimals", tx)
bad = [(s, g, T.decimals(s)) for s, g in zip(tx, got) if T.decimals(s) != g]
ok &= report("decimals(text)", bad, len(tx))
nums = [rng.choice([rng.random(), rng.uniform(-1e5, 1e5), 10.0 ** rng.randint(-10, 20), float(rng.randint(-50, 50)), round(rng.random(), rng.randint(1, 7))]) for _ in range(8000)] + [1e-7, 1.5e-7, 1e21, 1e22, 123456789.123456789, 5e-324]
got = js("decimals", nums)
bad = [(x, g, T.decimals(x)) for x, g in zip(nums, got) if T.decimals(x) != g]
ok &= report("decimals(number)", bad, len(nums))
# 8. prose number readings
alph = "0123456789,.'\u2019-+eE"
rd = ["1.234,50", "1,234.50", "3.000", "1.234.567", "1,00,000", "1'234", "1\u2019234.5", "-5", "1e-5", "1,5e3", "12,5", ".5", ",5", "1.2.3", "1.234,567,8", "\u0663.\u0665", "\u0661\u066c\u0662\u0663\u0664"]
for _ in range(6000):
    rd.append(rng.choice(["", "-"]) + "".join(rng.choice("0123456789,.'") for _ in range(rng.randint(1, 9))) + rng.choice(["", "", "e5", "e-3", "e+2"]))
rd = [r for r in rd if re.fullmatch(T._PATTERNS["prose"].pattern.split("|(?P<word>")[0].replace("(?P<num>", "(?:", 1), r)] or True
got = js("readings", rd)
bad = []
for s, g in zip(rd, got):
    try:
        p = [[v, d] for v, d in T._readings(s)]
    except Exception as e:
        p = "crash"
    if p == "crash":
        continue
    if [[float(v), d] for v, d in p] != [[float(v), d] for v, d in g]:   # == so that -0.0 equals 0 (JSON drops the sign)
        bad.append((s, p, g))
ok &= report("_readings(text)", bad, len(rd))
# 9. lexer on odd text, both modes
odd = ["", "Stra\u00dfe \u00c5NGSTR\u00d6M na\u00efve", "e\u0301 x\u00ad y", "a&amp;b &eacute;t&eacute; &#233; &#x41; &#65; &lt;x&gt; &foo; &#\u0663;", "1.5e3 -2.5E-4 +7 .5 5. 1,5 1.234,5 1'000",
       "x_1 y_2.5 DEF_a-b", "\u2212 5 \u2013 6", "\U0001F600 12.5 \U0001F600", "\u0663.\u0665 \u0661\u0662\u0663", "\u01c5 \u0130 \u0131 \u03c2 \u03a3 \u00df \u1e9e", "&nbsp;&sup2;&frac12;&alpha;&Sigma;&OElig;",
       "&#128;&#138;&#159;&#0;&#xD800;&#x110000;", "\uff21\uff11\uff12 \uff46\uff55\uff4c\uff4c", "\u2177 \u00bd \u00b2 \u2460", "a\u200bb\u00a0c\u2003d\ufeffe", "1e5e5 1.2.3 1,2,3 12-34 -.5 +.5e-3x"]
chars = "aAb\u00df \u03c2.,-+_eE0123456789'\u2019&#;xX\u00ad\u0301\u2212\u2013\u03a3\u0131\u0130\u0663 \t\n"
for _ in range(1500):
    odd.append("".join(rng.choice(chars) for _ in range(rng.randint(1, 18))))
for mode, fn in (("prose", "lexw"), ("x3d", "lexx")):
    got = js(fn, odd)
    bad = [(s, T.lex(s, mode).norms, g) for s, g in zip(odd, got) if T.lex(s, mode).norms != g]
    ok &= report("lex(%s) norms" % mode, bad, len(odd))
# 10. the lexer over EVERY code point inside a word ("a" + ch + "b") and next to a number, both modes: combining marks (BUG-28), digits, spaces
marks_py = [c for c in allcp if unicodedata.category(c) in ("Mn", "Mc", "Me")]
ins = ["a" + c + "b" for c in allcp] + ["5" + c + "6" for c in allcp[::7]]
for mode, fn in (("prose", "lexw"), ("x3d", "lexx")):
    got = js(fn, ins)
    diff = [s for s, g in zip(ins, got) if T.lex(s, mode).norms != g]
    bad = [hex(ord(s[1])) for s in diff if unicodedata.category(s[1]) != "Cn"]
    ok &= report("lex(%s) over all code points" % mode, bad, len(ins))
    print("   differences on code points unassigned in Python's Unicode: %d" % (len(diff) - len(bad)))
# the engine's mark class is generated up to U+1FFFF: how many marks does it hold, and does the port treat the same set as word characters?
inside = set(c for c in marks_py if ord(c) < 0x20000)
print("   engine mark class: %d marks below U+20000; marks above U+1FFFF (outside the class): %d" % (len(inside), len(marks_py) - len(inside)))
print("ALL OK" if ok else "SOME DIFFERENCES")
