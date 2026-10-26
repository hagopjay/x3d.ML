"""x3dprov 0.1 (scratch copy retyped from hagopjay/x3d.ML main 5379a80 src/x3dprov.py via the GitHub MCP read; used only to reproduce DESIGN.md claims).
A hash-chained provenance record carried inside an X3D file's own <head><meta> statements.
"""
import hashlib
import json
import re
from lxml import etree

SCHEMA = "x3dprov/0.1"
PREFIX = "x3dprov."
ZERO = "0" * 64
_STEP_RE = re.compile(r"^x3dprov\.step\.(\d+)$")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _parse(xml):
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False, no_network=True, remove_comments=True)
    return etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml, parser)


def _strip_prov(root):
    for m in root.xpath("//head/meta[starts-with(@name,'x3dprov.')]"):
        m.getparent().remove(m)
    return root


_META_RE = re.compile(r"""\s*<meta\s+name=(["'])x3dprov\.[^"']*\1[^>]*?/>""")


def content_hash(xml) -> str:
    text = xml.decode("utf-8", "replace") if isinstance(xml, bytes) else xml
    try:
        root = _strip_prov(_parse(text))
    except etree.XMLSyntaxError:
        return _sha(re.sub(r"\s+", " ", _META_RE.sub("", text)).strip().encode("utf-8"))
    for el in root.iter():
        if el.text is not None and not el.text.strip():
            el.text = None
        if el.tail is not None and not el.tail.strip():
            el.tail = None
    return _sha(etree.tostring(root, method="c14n"))


def _dumps(d) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


_STEP_META = re.compile(r"""<meta\s+name=(["'])x3dprov\.step\.(\d+)\1\s+content=(["'])(.*?)\3\s*/>""", re.S)


def read_steps(xml):
    from html import unescape
    text = xml.decode("utf-8", "replace") if isinstance(xml, bytes) else xml
    return sorted((int(m.group(2)), unescape(m.group(4))) for m in _STEP_META.finditer(text))


def add_step(xml_before, step: dict, xml_after=None) -> str:
    steps = read_steps(xml_before)
    out_xml = xml_after if xml_after is not None else xml_before
    prev_json = steps[-1][1] if steps else None
    rec = dict(step)
    rec.setdefault("input_sha256", json.loads(prev_json)["output_sha256"] if prev_json else content_hash(xml_before))
    rec["output_sha256"] = content_hash(out_xml)
    rec["prev"] = _sha(prev_json.encode("utf-8")) if prev_json else ZERO
    n = steps[-1][0] + 1 if steps else 1
    metas = []
    if not steps:
        metas.append('<meta name="x3dprov.version" content="%s"/>' % SCHEMA)
    for k, c in steps:
        metas.append('<meta name="x3dprov.step.%d" content=%s/>' % (k, _attr(c)))
    metas.append('<meta name="x3dprov.step.%d" content=%s/>' % (n, _attr(_dumps(rec))))
    if steps:
        metas.insert(0, '<meta name="x3dprov.version" content="%s"/>' % SCHEMA)
    stripped = _META_RE.sub("", out_xml)
    return _inject_meta(stripped, "".join(metas))


def _attr(s):
    return '"' + s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;") + '"'


def _inject_meta(xml, metas):
    if re.search(r"</head>", xml):
        return re.sub(r"</head>", lambda m: metas + "</head>", xml, count=1)
    m = re.search(r"<head\b[^>]*/>", xml)
    if m:
        return xml[:m.start()] + "<head>" + metas + "</head>" + xml[m.end():]
    m = re.search(r"<X3D\b[^>]*>", xml)
    return xml[:m.end()] + "<head>" + metas + "</head>" + xml[m.end():]


def verify(xml) -> dict:
    steps = read_steps(xml)
    if not steps:
        return {"ok": False, "status": "no-record", "steps": 0, "problems": ["no x3dprov.step metas"]}
    problems, prev_json, prev_out = [], None, None
    for i, (n, content) in enumerate(steps, 1):
        if n != i:
            problems.append(f"step numbering gap: expected {i}, found {n}")
        try:
            rec = json.loads(content)
        except ValueError:
            problems.append(f"step {n}: not JSON"); continue
        want = _sha(prev_json.encode("utf-8")) if prev_json else ZERO
        if rec.get("prev") != want:
            problems.append(f"step {n}: prev hash does not match step {n-1} (step removed or edited)")
        if prev_out is not None and rec.get("input_sha256") != prev_out:
            problems.append(f"step {n}: input_sha256 differs from step {n-1} output (content changed between steps, untracked)")
        prev_json, prev_out = content, rec.get("output_sha256")
    cur = content_hash(xml)
    if problems:
        return {"ok": False, "status": "broken-chain", "steps": len(steps), "problems": problems}
    if cur != prev_out:
        return {"ok": False, "status": "stale", "steps": len(steps),
                "problems": ["file content differs from last recorded output (edited after the last step, untracked)"]}
    return {"ok": True, "status": "verified", "steps": len(steps), "problems": []}


def summary(xml):
    return [json.loads(c) for _, c in read_steps(xml)]
