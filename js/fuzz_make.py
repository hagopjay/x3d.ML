"""Random claims, expectations from the Python engine (read only), same row format as vectors.json (plus optional "sources").
usage: python3 -I -B fuzz_make.py <engine_dir> <out.json> [rows] [seed]
Then: node test_vectors.js <out.json> <disagreements-out.json>"""
import sys, json, random, math, hashlib, re
sys.path.insert(0, sys.argv[1])
import x3dtrace as T
out_path = sys.argv[2]; N = int(sys.argv[3]) if len(sys.argv) > 3 else 20000; seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
rng = random.Random(seed)
FIELDS = ["radius", "height", "size", "translation", "rotation", "angle", "transparency", "diffuseColor", "cycleInterval", "intensity",
          "scale", "center", "DEF", "name", "string", "//*[@DEF='n']/@radius", "//*[@DEF='n']/@rotation", "//*[@DEF='n']/@diffuseColor",
          "/X3D/Scene/Transform[@DEF='A']/@translation", "Material[m].emissiveColor", "x"]
FTYPES = ["", "", "", "", "length", "time", "angle", "rotation", "color", "identifier", "fraction", "weird"]
UN = ["m", "cm", "mm", "km", "ft", "in", "feet", "inches", "yd", "mi", "s", "ms", "min", "h", "hours", "seconds", "kg", "pcs", "x"]
WORDS = ["the", "radius", "of", "about", "turn", "deg", "Degrees", "RADIANS", "rad", "percent", "per cent", "pct", "and", "by", "Gr\u00f6\u00dfe", "Stra\u00dfe", "\u039f\u0394\u039f\u03a3",
         "na\u00efve", "\u01c5", "\u00df", "x", "y", "Z", "vertical", "up", "red", "Grey", "BLUE", "green", "orange", "one", "Two", "three", "half", "a dozen",
         "ten", "hundred", "colour", "rgb", "#", "\u00b0", "%", "-", "\u2013", "\u2212", "+", "m", "cm", "units", "size"]
NOISE = ["", "", "As asked: ", "Note \u2014 ", "\u00c4\u00d6\u00dc 12 ", "\U0001F600 ", "\n", "  ", "\u00a0", "x_1 ", "(1,234.5) "]

def num(x=None):
    if x is None:
        x = rng.choice([rng.randint(-20, 400), round(rng.uniform(-10, 100), rng.randint(0, 5)), rng.randint(-8, 8) / 2 ** rng.randint(0, 5),
                        rng.choice([0.25, 0.125, 0.375, 0.5, 2.5, 0.35, 1.005, 2.675, 1e-5, 1e5, 123456.789, 0, 1, 90, 180, 255, 1.5708, 3.14159, 0.0254])])
    return x

def fmt(x, style=None):
    style = style or rng.choice(["plain", "plain", "plain", "comma", "thou", "thoudot", "space", "exp", "trail", "lead", "arabic", "apos", "round"])
    s = repr(float(x)) if isinstance(x, float) else str(x)
    if style == "comma": return s.replace(".", ",")
    if style in ("thou", "thoudot", "space", "apos") and abs(x) >= 1000:
        ip, _, fp = ("%f" % x if "e" in s else s).partition(".")
        g = "{:,}".format(abs(int(float(ip)))) if True else ip
        sep = {"thou": ",", "thoudot": ".", "space": " ", "apos": "'"}[style]
        return ("-" if x < 0 else "") + g.replace(",", sep) + ((("," if sep == "." else ".") + fp) if fp and fp != "0" else "")
    if style == "exp": return "%g" % x if rng.random() < .5 else "%e" % x
    if style == "trail": return (s + "0" * rng.randint(1, 3)) if re.fullmatch(r"-?\d+\.\d+", s) else (s + ".0" if re.fullmatch(r"-?\d+", s) else s)
    if style == "lead": return s.lstrip("-0") if rng.random() < .3 and 0 < abs(x) < 1 else s
    if style == "arabic": return s.translate(str.maketrans("0123456789", "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669"))
    if style == "round": return ("%." + str(rng.randint(0, 4)) + "f") % x
    return s

def perturb(v):
    r = rng.random()
    if isinstance(v, (int, float)):
        return v if r < .5 else (-v if r < .6 else v + rng.choice([1, -1, 0.001, 1e-7, 0.5]))
    return v

def val_scalar():
    x = num(); r = rng.random()
    if r < .4: return x
    if r < .7: return fmt(x, "plain")
    return fmt(perturb(x), rng.choice(["plain", "round", "trail", "comma"]))

def quote_scalar(v):
    try: x = float(v)
    except Exception: x = num()
    base = rng.choice([x, x * math.pi / 180, x * 180 / math.pi, x / 100, x * 100, x * 0.3048, x / 0.3048, x * 0.0254, x * 60, x / 60, x * 0.01, x * 1000, x * 0.001])
    if rng.random() < .5: base = round(base, rng.randint(0, 5))
    n = fmt(base)
    u = rng.choice(["", "", " " + rng.choice(UN), " " + rng.choice(["degrees", "deg", "\u00b0", "DEG", "Degs", "rad", "radians", "rad\u0131ans", "%", "percent", "per cent", "pct"]),
                    rng.choice(["\u00b0", "%", "\u00ba"]), "  " + rng.choice(UN), "\u00a0m", " Ms", " m\u00e9"])
    pre = rng.choice(["", "", "radius of ", "- ", "minus ", "\u2212", "x = ", "approx. ", "a ", rng.choice(WORDS) + " ", "- about "])
    return pre + n + u + rng.choice(["", "", " tall", " east", ".", ", ok"])

def val_vector(k=None):
    k = k or rng.choice([2, 3, 3, 3, 4, 4])
    comps = [rng.choice([num(), 0, 0, 1, -1, rng.randint(0, 255)]) for _ in range(k)]
    if rng.random() < .15: comps = [comps[0]] * k
    if rng.random() < .15: comps = [rng.choice([0, 0, 1, 0.5, 0.2, 0.8, 1]) for _ in range(k)]
    sep = rng.choice([" ", " ", ",", ", "])
    if rng.random() < .1: return [float(c) for c in comps]
    return sep.join(fmt(c, rng.choice(["plain", "plain", "round", "trail"])) for c in comps)

def quote_vector(v):
    comps = [float(c) for c in (v if isinstance(v, list) else v.replace(",", " ").split())]
    r = rng.random()
    if r < .25: parts = [fmt(c, "plain") for c in comps]
    elif r < .4: parts = [fmt(c, rng.choice(["round", "comma"])) for c in comps]
    elif r < .5: parts = [fmt(c, "plain") for c in reversed(comps)]
    elif r < .6: parts = [fmt(c, "plain") for c in comps if c != 0] or ["0"]
    elif r < .7: parts = [fmt(c * 255, "round") for c in comps] if len(comps) == 3 else [fmt(comps[0], "plain")]
    elif r < .8:
        h = "".join("%02x" % max(0, min(255, int(round(c * 255)))) for c in comps[:3])
        return rng.choice(["#", "", "color #", "0x"]) + rng.choice([h, h.upper()]) + rng.choice(["", " ok", "ff"])
    elif r < .9: return rng.choice(WORDS) + " " + rng.choice(["red", "Grey", "BLUE", "green", "orange", "white", "black", "pink", "navy", "purple"]) + " " + rng.choice(WORDS)
    else: parts = [fmt(comps[0], "plain")] + [rng.choice(WORDS)] + [fmt(c, "plain") for c in comps[1:]]
    if len(comps) == 4 and rng.random() < .6:
        ang = comps[3]
        a = rng.choice([fmt(math.degrees(ang), "round") + rng.choice([" degrees", "\u00b0", " deg", ""]), fmt(ang, "plain") + rng.choice([" rad", "", " radians"])])
        return "%s %s about the %s axis" % (rng.choice(["turn", "rotate", ""]), a, rng.choice(["x", "y", "Z", "vertical", "up", "X"]))
    if rng.random() < .3: parts = [p + " " + rng.choice(UN) for p in parts]
    return rng.choice(["", "", "size ", "scale "]) + rng.choice([" ", " ", ", ", " x ", " and "]).join(parts)

def xml_row():
    attrs = {"translation": val_vector(3) if True else "", "size": val_vector(3), "radius": str(num()), "diffuseColor": val_vector(3), "rotation": val_vector(4), "string": rng.choice(["Hello world", "Gr\u00f6\u00dfe", "x &amp; y", "&eacute;t&eacute; &#233;"])}
    names = rng.sample(list(attrs), rng.randint(1, 4))
    body = "".join(" %s=%s%s%s" % (n, q, (attrs[n] if isinstance(attrs[n], str) else " ".join(map(repr, attrs[n]))), q) for n in names for q in [rng.choice(["'", '"'])])
    text = rng.choice(["", "<?xml version='1.0'?>\n"]) + "<X3D><Scene><Transform DEF='A'%s><Shape DEF='B'%s/></Transform></Scene></X3D>" % (body, body if rng.random() < .4 else "")
    n = rng.choice(names); val = attrs[n] if isinstance(attrs[n], str) else " ".join(map(repr, attrs[n]))
    i = text.index(n + "=")
    j = text.index(val, i) + len(val)
    quote = text[i:j + 1] if rng.random() < .8 else val
    if rng.random() < .2: text = text[max(0, i - 40):j + 40]
    value = val if rng.random() < .6 else perturb_text(val)
    fld = rng.choice(["//*[@DEF='A']/@" + n, "//*[@DEF='B']/@" + n, "//*[@DEF='B']/@" + n, "/X3D/Scene/Transform/@" + n, "/X3D/Scene/Transform/Shape/@" + n, n, "Transform." + n])
    return "x3d", text, {"field": fld, "value": value, "quote": quote}

def perturb_text(v):
    p = v.split()
    if not p: return v
    r = rng.random()
    if r < .3: return " ".join(p[::-1])
    if r < .5: return "-" + v
    if r < .7: return " ".join(p[:-1]) or v
    return v.replace("1", "2", 1)

def color_row():
    comps = [round(rng.random(), rng.randint(1, 3)) if rng.random() < .8 else rng.choice([0, 1]) for _ in range(3)]
    if rng.random() < .6: comps[rng.randrange(3)] = 1; comps[rng.randrange(3)] = rng.choice([0, 0.1, 0.3])
    if rng.random() < .3: comps = [1, 0, round(rng.random(), 2)]    # red side of magenta: negative hue before the modulo
    n1, n2 = rng.choice(list(T.COLORS)), rng.choice(list(T.COLORS))
    q = rng.choice(["%s", "a %s one", "light %s", "dark %s paint", "%s-ish", "%s and %s", "Paint it %s.", "%s %s"]) % ((n1, n2) if "%s and" in "" else (n1,)) if False else \
        rng.choice(["%(a)s", "a %(a)s one", "light %(a)s", "dark %(a)s paint", "%(a)s and %(b)s", "%(a)s %(b)s"]) % {"a": n1, "b": n2}
    return "text", None, {"field": rng.choice(["diffuseColor", "emissiveColor", "x"]), "value": " ".join(fmt(c, "plain") for c in comps), "quote": q,
                          "ftype": rng.choice(["", "", "color"])}

def tie_row():
    dpq = rng.randint(1, 4); dpv = rng.randint(1, 5)
    k = rng.randint(-40, 40) / 2 ** rng.randint(1, 6)
    qs = ("%." + str(dpq) + "f") % k if rng.random() < .5 else repr(k)
    vs = ("%." + str(dpv) + "f") % (k + rng.choice([0, 0, 0.0001, -0.0001, 0.005]))
    return "text", None, {"field": rng.choice(["radius", "x"]), "value": rng.choice([vs, float(vs)]), "quote": rng.choice(["", "radius ", "about "]) + qs}

def long_row():
    comps = [rng.choice([rng.randint(-9, 9), round(rng.uniform(-5, 5), rng.randint(1, 4)), 0.0, 1.0, 1e-5, 1e16, 1.5e22]) for _ in range(rng.randint(60, 90))]
    txt = " ".join(repr(float(c)) if isinstance(c, float) else str(c) for c in comps)
    val = rng.choice([txt, [float(c) for c in comps], [c for c in comps], txt.replace(" ", ", ")])
    q = rng.choice([txt, txt, txt[:len(txt) // 2], txt + " 7", " ".join(str(c) for c in comps)])
    return "text", "coordIndex='%s'" % q if rng.random() < .5 else None, {"field": "point", "value": val, "quote": q}

NNBSP, THIN, FIG, EMSP = chr(0x202f), chr(0x2009), chr(0x2007), chr(0x2003)
DOTLESS, DOTTED, LONGS, DASH, MINUS = chr(0x131), chr(0x130), chr(0x17f), chr(0x2013), chr(0x2212)
COLORN = list(T.COLORS)

def v4_row():
    """Rows aimed at the v4 engine changes: consecutive vector numbers, zero-fill, unit conflicts, degrees for radians, axis flips,
    colour names, number words, 'in', dates, percent, hex, rad2deg slack, grouped thousands, detached minus, long arrays, bad sources."""
    k = rng.randrange(20)
    kind, text, claim = "text", None, None
    if k == 0:   # vectors on consecutive numbers, extra numbers around, units per component
        comps = [rng.choice([1, 2, 3, 0, 0.5, -1, 2.5, 6, 0.4]) for _ in range(rng.choice([2, 3, 3, 4]))]
        v = " ".join(fmt(c, "plain") for c in comps)
        nums = [fmt(c, "plain") + rng.choice(["", "", " m", " cm", " ft", " mm", " in", " s", " %", " degrees"]) for c in comps]
        extra = [rng.choice(["7", "9 cm", "x", "and", "by", "8 m"]) for _ in range(rng.randint(0, 2))]
        parts = nums[:]
        for e in extra: parts.insert(rng.randint(0, len(parts)), e)
        if rng.random() < .3: parts = parts[::-1]
        q = rng.choice(["", "size ", "a box of "]) + rng.choice([" ", " x ", ", ", " and "]).join(parts) + rng.choice(["", " tall", " in front of"])
        claim = {"field": rng.choice(["size", "translation", "scale", "center", "x", "height"]), "value": v, "quote": q}
    elif k == 1:   # zero-fill, with and without every component stated
        comps = [0, 0, 0]
        for i in rng.sample(range(3), rng.randint(1, 2)): comps[i] = rng.choice([2, 1.5, -3, 4])
        v = " ".join(fmt(c, "plain") for c in comps)
        q = rng.choice(["{n} m above", "translation=\"{full}\"", "{full}", "{n}", "{n} and {n2}", "move {n} m east", "{full} m"]).format(
            n=fmt([c for c in comps if c][0], "plain"), n2=fmt(comps[-1], "plain"), full=v)
        claim = {"field": rng.choice(["translation", "size", "x", "diffuseColor"]), "value": v, "quote": q}
    elif k == 2:   # rotation: axis words, flips, degrees for radians
        ax = rng.choice([(0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)])
        ang = rng.choice([1.5708, -1.5708, 0.7854, -0.7854, 3.1416, 90, -90, 0.5236])
        v = "%s %s %s %s" % (ax + (ang,))
        word = rng.choice(["x", "y", "z", "vertical", "up", "Y"])
        deg = fmt(abs(ang) * (180 / math.pi if abs(ang) < 7 else 1), "round")
        q = rng.choice(["turn {d} degrees about the {w} axis", "{sg}{d} deg around {w}", "rotate {r} rad about {w}", "turn {d} about {w}", "{v}",
                        "{v} degrees", "orientation {v}", "-{d} degrees about the {w} axis", "{d}{o} about y"]).format(
            d=deg, w=word, sg=rng.choice(["", "-"]), r=fmt(abs(ang), "plain"), v=v, o=rng.choice(["\xb0", " deg"]))
        claim = {"field": rng.choice(["rotation", "orientation", "x"]), "value": v, "quote": q, "ftype": rng.choice(["", "", "rotation"])}
    elif k == 3:   # colours: names of other colours, hex, rgb, numbers
        comps = [rng.choice([0, 1, 0.5, 0.8, 0.2, 0.502]) for _ in range(3)]
        v = " ".join(fmt(c, "plain") for c in comps)
        hx = "".join("%02x" % int(round(c * 255)) for c in comps)
        q = rng.choice(["{n}", "a {n} thing", "{n} and {m}", "#{h}", "{h}", "color {h}", "{h2}", "rgb({r}, {g}, {b})", "{r} {g} {b}", "{v}", "facade", "123456", "#123456 {n}"]).format(
            n=rng.choice(COLORN), m=rng.choice(COLORN), h=hx, h2=hx.upper(), r=int(round(comps[0] * 255)), g=int(round(comps[1] * 255)), b=int(round(comps[2] * 255)), v=v)
        claim = {"field": rng.choice(["diffuseColor", "emissiveColor", "color", "x"]), "value": v, "quote": q}
    elif k == 4:   # number words and contradictions
        w = rng.choice(["one", "two", "three", "four", "five", "ten", "twelve", "half", "dozen", "hundred", "twenty"])
        val = rng.choice([1, 2, 3, 4, 5, 10, 12, 0.5, 100, 20, 7])
        q = rng.choice(["{w}", "{w} metres", "a {w} cubes", "about {w} seconds", "{w} {w}", "{w} 5", "radius {w}"]).format(w=w)
        claim = {"field": rng.choice(["radius", "x", "cycleInterval", "size"]), "value": rng.choice([val, str(val), " ".join([str(val)] * 3)]), "quote": q}
    elif k == 5:   # "in" as unit or preposition
        n = rng.choice([2, 3, 6, 0.5])
        q = rng.choice(["{n} in front of the door", "{n} in the middle", "{n} in wide", "{n} in. wide", "{n} in", "{n} in x {n} in", "{n} in, {n} in", "{n} in" + DOTLESS,
                        "{n} in" + chr(0xe9), "{n} inch", "{n} IN thick", "{n} in 5", "{n} in" + LONGS + "x", "{n} in\n", "{n} in diameter", "{n} in by 4", "{n} in the", "{n} in radius"]).format(n=n)
        v = rng.choice([n, fmt(n * 0.0254, "round"), str(n), "%s %s %s" % (n, n, n), fmt(n * 0.0254, "plain")])
        claim = {"field": rng.choice(["radius", "size", "x", "height"]), "value": v, "quote": q}
    elif k == 6:   # percent against fractions, rad2deg slack
        if rng.random() < .5:
            x = rng.choice([50, 0.5, 5, 25, 0.25, 100, 1, 80])
            q = rng.choice(["{p} %", "{p} percent", "{p}%", "{f}", "{p} per cent"]).format(p=rng.choice([50, 5, 25, 80, 100]), f=rng.choice([0.5, 50, 0.25]))
            claim = {"field": rng.choice(["transparency", "intensity", "ambientIntensity", "shininess", "x", "radius"]), "value": rng.choice([x, str(x)]), "quote": q}
        else:
            deg = rng.choice([90, 45, 180, 30, 57.2958, 10, 1, 360, 114.592])
            rad = deg * math.pi / 180
            q = rng.choice(["{a} rad", "{b} radians", "{c} rad", "{d} rad", "{a}rad"]).format(a=("%.4f" % rad), b=("%.3f" % rad), c=("%.2f" % rad), d=("%.5f" % rad))
            claim = {"field": rng.choice(["angle", "rotation", "x", "startAngle"]), "value": rng.choice([deg, str(deg), "%g" % deg, float(int(deg))]), "quote": q}
    elif k == 7:   # space-grouped thousands
        x = rng.choice([1234, 1234567, 12345, 123456, 1234.5, 1234567.89, 999, 12345.678, 1000, 123])
        s = "%.2f" % x if isinstance(x, float) else str(x)
        ip, _, fp = s.partition(".")
        groups = []
        while ip: groups.insert(0, ip[-3:]); ip = ip[:-3]
        sep = rng.choice([" ", "\xa0", NNBSP, THIN, FIG, "  ", EMSP, " "])
        q = rng.choice(["", "total ", "about "]) + sep.join(groups) + (rng.choice([",", "."]) + fp if fp else "") + rng.choice(["", " EUR", " m", " kg"])
        claim = {"field": rng.choice(["radius", "x", "height"]), "value": rng.choice([x, str(x), fmt(x, "plain")]), "quote": q}
    elif k == 8:   # detached minus and ranges
        n = rng.choice([5, 12, 1014.5, 3, 0.5])
        pre = rng.choice(["Discount (5%) - ", "10 - ", "x - ", "- ", "temperature - ", "(3) - ", "5% - ", "a 10 - ", "pages 3 - ", "10 " + DASH + " ", "10 " + MINUS + " ", "-", "10 -",
                          "word " + "w " * 40 + "- ", "1 " + "w " * 120 + "- ", "end. - ", "7 m - ", "\n- ", " - "])
        q = pre + fmt(n, "plain") + rng.choice(["", " m", " EUR"])
        claim = {"field": rng.choice(["radius", "x", "height"]), "value": rng.choice([-n, n, str(-n), "-" + fmt(n, "plain")]), "quote": q}
    elif k == 9:   # long arrays
        comps = [rng.choice([0, 1, 2, 3, 0.5, 1.25, -1, 100000]) for _ in range(rng.randint(60, 80))]
        if rng.random() < .3: comps = comps[:rng.choice([64, 65, 66])]
        v = rng.choice([" ".join(fmt(c, "plain") for c in comps), [float(c) for c in comps], [str(c) for c in comps], ", ".join(fmt(c, "plain") for c in comps)])
        qc = comps[:]
        r = rng.random()
        if r < .2: qc[rng.randrange(len(qc))] += 1
        elif r < .3: qc = qc[1:]
        q = rng.choice(["", "coordIndex='", "point "]) + " ".join(rng.choice([fmt(c, "plain"), repr(float(c))]) for c in qc) + rng.choice(["", "'", " 7"])
        claim = {"field": rng.choice(["point", "coordIndex", "x"]), "value": v, "quote": q}
    elif k == 10:   # dates
        d = rng.choice(["2025-04-11", "2025-11-11", "11.04.2025", "04/11/2025", "2025-02-30", "1.2.3", "11-11-11", "2025.11.11", "31.12.99", "5/6/24", "2025-1-1"])
        q = rng.choice(["{d}", "11 11 2025", "11 2025", "November 11, 2025", "11. marraskuu 2025", "2025", "April 11 2025", "on 11/11/2025", "11.11.25", "1 1 2025", "1 2025 11",
                        "Order 4 of 11 in 2025", "11 April 2025", "1 jan 2001", "2 2 2002", "02/15/2026", "Nov 11"]).format(d=d)
        claim = {"field": rng.choice(["x", "date", "name"]), "value": d, "quote": q}
    elif k == 11:   # sources: unknown id, binary only, moved, line hints
        q = rng.choice(["radius 3", "3 m", "alpha beta", "x 1 2 3"])
        lines = [rng.choice(["", "see: ", "a "]) + q + rng.choice(["", " ok"]) for _ in range(rng.randint(2, 5))]
        text = "\n".join(lines)
        claim = {"field": rng.choice(["radius", "x"]), "value": rng.choice(["3", 3, "1 2 3", "alpha"]), "quote": q, "line": rng.choice([1, 2, 3, 4, 0, -1, 9])}
        if rng.random() < .3: claim["prefix"] = rng.choice(["see", "a", ""])
    elif k == 12:   # exactness checks of _eq: printed zeros, rounded displays
        a = rng.choice([0.04, 0.004, 0.25, 0.05, 0.349, 1.005, 0.0, 0.5, 0.01])
        q = rng.choice(["0.0", "0.00", "0", "0.1", "0.3", "0.35", "0.04", "0.0400", "0", "0.00 m", "0.5", "1.0"])
        claim = {"field": rng.choice(["radius", "transparency", "x"]), "value": rng.choice([a, str(a), "%.3f" % a, "%.4f" % a]), "quote": rng.choice(["", "about "]) + q}
    elif k == 13:   # percent / unit conflicts per component in vectors
        v = rng.choice(["1 2 3", "0.01 0.02 0.03", "50 50 50", "0.5 0.5 0.5", "2 2", "1 1 1"])
        q = rng.choice(["1 cm 2 cm 3 cm", "1 m 2 m 3 m", "1 ft 2 3", "50 % 50 % 50 %", "1 2 3 degrees", "1 2 3 m", "0.01 m 0.02 m 0.03 m", "1 2 3 ft", "1 km 2 km 3 km", "2 2 mm"])
        claim = {"field": rng.choice(["size", "scale", "translation", "x", "intensity"]), "value": v, "quote": q}
    elif k == 14:   # numeric strings in list values
        lst = rng.choice([[1, 2, 3], ["1", "2", "3"], [" 1 ", "2.5", 3], ["1", "x", "3"], [True, 1], [1.5, "2.5"], ["a"], ["1", "2"]])
        q = rng.choice(["1 2 3", "1, 2.5, 3", "1 2", "1.5 2.5", "one two"])
        claim = {"field": rng.choice(["size", "x"]), "value": lst, "quote": q}
    elif k == 15:   # unknown / odd sources
        q = "radius 2.5 m"
        text = "A. " + q
        claim = {"field": "radius", "value": rng.choice([2.5, "2.5", "3"]), "quote": q, "source": rng.choice(["nope", "it's", 'say "x"', "tab\there", "\xe9", "ok"])}
    elif k == 16:   # identifiers, text values, reformatted identifiers
        v = rng.choice(["7200-4453-21", "7200445321", "Cube1", "cube1", "A1", "hello world", "Hello", "x_y", "main hall"])
        q = rng.choice(["7200 4453 21", "7200-4453-21", "ref 7200445321", "CUBE1 here", "DEF=\"Cube1\"", "the main hall", "Hello, world", "hello_world", "x y"])
        claim = {"field": rng.choice(["DEF", "name", "x", "string"]), "value": v, "quote": q}
    elif k == 17:   # a dash at the very start of the 200-code-point window before the number (long token between), astral characters inside
        m = rng.randint(185, 205)
        tok = ("x" * (m - 20)) + "\U0001F600" * 20 if rng.random() < .5 else "x" * m
        q = rng.choice(["5 - ", "(5) - ", "a - ", "5 -", "7 \u2013 "]) + tok + rng.choice([" 7", " 7 m", " EUR 7", " a 7", " a b 7"])
        claim = {"field": rng.choice(["radius", "x"]), "value": rng.choice([-7, 7, "-7"]), "quote": q}
    elif k == 18:   # words with combining marks of other scripts around and inside the quote
        w = rng.choice([chr(0x928) + chr(0x92e) + chr(0x938) + chr(0x94d) + chr(0x924) + chr(0x947), chr(0x5e9) + chr(0x5c1) + chr(0x5dc) + chr(0x5d5) + chr(0x5dd),
                        chr(0xe17) + chr(0xe35) + chr(0xe48), chr(0x628) + chr(0x64e) + chr(0x62a) + chr(0x650), "e" + chr(0x301) + "a" + chr(0x20d7), chr(0x1d165) + "a",
                        chr(0x3b1) + chr(0x342), "a" + chr(0xe0100), chr(0x1e8d0) + "b"])
        v = rng.choice(["5", "5 5", w, "A " + w])
        q = rng.choice(["{w} 5", "5 {w}", "5{w}", "{w} 5 m {w}", "A {w}", "{w}", "{w}5 6", "radius {w} 5"]).format(w=w)
        claim = {"field": rng.choice(["radius", "x", "name", "string"]), "value": v, "quote": q}
    else:   # fractions, broadcast with units and conflicts
        n = rng.choice([2, 3, 0.5, 6])
        q = rng.choice(["radius {n}", "radius {n} cm", "uniform size {n} m", "{n} ft cube", "scale {n}", "{n} s loop", "{n} min"]).format(n=n)
        claim = {"field": rng.choice(["size", "scale", "x", "cycleInterval", "radius"]), "value": " ".join([str(n)] * rng.choice([2, 3])) if rng.random() < .8 else n, "quote": q}
    if "ftype" not in claim and rng.random() < .12:
        claim["ftype"] = rng.choice(FTYPES)
    return kind, text, claim

def text_row():
    r = rng.random()
    if r < .03: return long_row()
    if r < .12: return color_row()
    if r < .2: return tie_row()
    r = rng.random()
    if r < .25:
        f = rng.choice(["DEF", "name", "string", "other", "radius"])
        v = rng.choice(["Cube1", "cube1", "main hall", "7200445321", "007", "Hello_World", "Stra\u00dfe", "STRASSE", "\u01c4 x", "\u03c2", "\u03c3 \u03bf", "tapaturma \u00e4", "1.2.3", "2025-04-11", "12.04.2025", "ab-cd", "x"])
        q = rng.choice([v, v.upper(), "the " + v, "7200-4453-21", "Part 7", "Strasse", "\u039f\u0394\u039f\u03a3", "\u01c4 X", 'DEF="%s"' % v, "main  hall", "Main\u00a0Hall", "Hello World", "ab-cd", "11.04.2025", "April 11 2025", "x"])
        return "text", None, {"field": f, "value": v, "quote": q}
    if r < .75:
        v = val_scalar(); return "text", None, {"field": rng.choice(FIELDS), "value": v, "quote": quote_scalar(v)}
    v = val_vector(); return "text", None, {"field": rng.choice(FIELDS), "value": v, "quote": quote_vector(v)}

POLICIES = [{}, {}, {}, {}, {}, {"conversions": ()}, {"conversions": ("deg2rad", "percent")}, {"conversions": ("unit", "numword")}, {"conversions": ("hex", "rgb255")},
            {"conversions": ("colorname", "broadcast", "axis")}, {"round_to_printed": False}, {"number_tolerance": 0.01}, {"number_tolerance": 1e-9}, {"length_scale": 0.3048},
            {"length_scale": 0.001}, {"match_reformatted_identifiers": False}, {"code_values_unchecked": True}, {"reworded_is_problem": True}, {"min_quote_words": 3},
            {"ambiguous_quote_is_check": True}, {"moved_is_check": True}, T.TracePolicy.strict().__dict__ if False else {"reworded_is_problem": True, "ambiguous_quote_is_check": True, "moved_is_check": True, "conversions": (), "round_to_printed": False}]

def pol_json(p): return {k: (list(v) if isinstance(v, tuple) else v) for k, v in p.items()}

def run(claim, sources, policy):
    pol = T.TracePolicy(**policy) if policy else T.TracePolicy()
    srcs = [T.Source(s["id"], s["text"], s["kind"]) for s in sources]
    it = T.check_claims([claim], srcs, pol).items[0]
    return {"verdict": it.verdict, "status": it.status, "value_status": it.value_status, "derivation": list(it.derivation), "occurrences": it.occurrences,
            "span": list(it.span) if it.span else None, "note": it.note, "source": it.source, "disambiguated_by": it.disambiguated_by}

rows = []
for i in range(N):
    r0 = rng.random()
    kind, text, claim = (v4_row() if r0 < .4 else xml_row() if r0 < .55 else text_row())
    quote = claim["quote"]
    if text is None:
        reps = rng.choice([1, 1, 1, 2, 3])
        text = rng.choice(NOISE) + (rng.choice(NOISE) + rng.choice(["", " and ", " / "]) + quote + rng.choice(["", ", ", " ... "])).join([""] * (reps + 1)) .strip() if False else \
            rng.choice(NOISE) + (rng.choice([" ... ", " ; ", "\n"])).join([rng.choice(["", rng.choice(WORDS) + " "]) + quote + rng.choice(["", " " + rng.choice(WORDS)]) for _ in range(reps)]) + rng.choice(NOISE)
        if rng.random() < .1: kind = "x3d"
    claim = dict(claim)
    if rng.random() < .08: claim["ftype"] = rng.choice(FTYPES)
    if rng.random() < .1: claim["quote"] = rng.choice(["", "   ", "nothing like it", quote.upper(), quote + " zzz", quote[: max(1, len(quote) // 2)]])
    if rng.random() < .05: claim["value"] = rng.choice([None, True, False, {"a": 1}, [1, 2, 3], [1.5, 2.5], ["a", "b"], [], [7], 3, 2.5, -0.0, 1e300, 12345678901234567890])
    texts = [{"id": "a", "text": text, "kind": "binary" if rng.random() < .02 else kind}]
    multi = rng.random() < .15
    if multi:
        other = {"id": "b", "text": rng.choice(NOISE) + rng.choice([quote, "unrelated"]) + rng.choice(NOISE), "kind": rng.choice(["text", "x3d", "binary"])}
        texts = [other, texts[0]] if rng.random() < .5 else texts + [other]
        claim["source"] = rng.choice(["a", "b", "missing", None])
        if rng.random() < .1: claim["document"] = rng.randint(0, 3)
    else:
        claim["source"] = "a"
    if rng.random() < .15 and quote.strip():   # context hints between repeated quotes
        if rng.random() < .5: claim["prefix"] = rng.choice(WORDS + ["", "As asked:"])
        if rng.random() < .5: claim["suffix"] = rng.choice(WORDS + ["", "ok"])
        if rng.random() < .3: claim["line"] = rng.randint(0, 4)
    pol = rng.choice(POLICIES)
    try:
        exp = run(claim, texts, pol)
    except Exception as e:
        exp = {"error": repr(e)[:100]}
    rows.append({"id": "fuzz-%05d" % i, "family": "fuzz", "kind": kind, "sources": texts, "claim": claim, "policy": pol_json(pol), "expect": exp})
json.dump({"engine_sha256_16": hashlib.sha256(open(sys.argv[1] + "/x3dtrace.py", "rb").read()).hexdigest()[:16], "python": sys.version.split()[0], "rows": rows},
          open(out_path, "w"))
import collections
print(len(rows), "rows;", dict(collections.Counter(r["expect"].get("verdict", "error") for r in rows)))
