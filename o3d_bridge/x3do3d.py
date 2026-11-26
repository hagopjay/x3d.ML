"""x3do3d: a bridge between X3D and Open3D / Open3D-ML (Intel ISL, MIT).

Directions
  X3D  -> Open3D   read_x3d(): PointSet, IndexedFaceSet, TriangleSet, IndexedTriangleSet (Transform stack applied,
                   DEF/USE of Coordinate/Color resolved) -> open3d PointCloud / TriangleMesh
  Open3D -> X3D    pointcloud_to_x3d(), mesh_to_x3d()
  Open3D-ML -> X3D segmentation_to_x3d(): per-point class labels (+ scores) become one Group per class, each with
                   a Coordinate DEF'd once and three lenses (class colour / source RGB / confidence), a class-keyed
                   MetadataSet, and an oriented box; boxes_to_x3d(): 3D detections as wire boxes with labels.
  X3D  -> Open3D-ML read_segmentation(): the labels back out of a scene this module wrote (the loop closes).

Frames. X3D is right-handed, Y up. Open3D-ML models (S3DIS, SemanticKITTI, KITTI) are Z up. The two helpers
x3d_to_ml() and ml_to_x3d() are proper rotations (det +1): ml = (x, -z, y), x3d = (x, z, -y).
Open3D-ML's S3DIS RandLA-Net also expects the floor near z = 0; see ml_frame_from_source().

Numbers in a scene are rounded (3 decimals for positions); the rounding is in every provenance record.
Needs numpy and lxml; open3d only for the Open3D-typed entry points (imported lazily).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
from lxml import etree

SCHEMA = "x3d-open3d-bridge/v1"
REFERENCE = "https://github.com/isl-org/Open3D-ML"

# ---------------------------------------------------------------------------------------------- frames
_X3D_TO_ML = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)  # (x,y,z) -> (x,-z,y)
_ML_TO_X3D = _X3D_TO_ML.T


def x3d_to_ml(p):
    return np.asarray(p, dtype=np.float64) @ _X3D_TO_ML.T


def ml_to_x3d(p):
    return np.asarray(p, dtype=np.float64) @ _ML_TO_X3D.T


# source up-axis conventions -> rotation into the ML (Z up) frame
UP_AXES = {
    "z": np.eye(3),
    "y": _X3D_TO_ML,                                                    # X3D / glTF / Unity-style Y up
    "-y": np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float64),  # camera frames (Redwood / RGB-D): y down, z forward
}


def ml_frame_from_source(points, up="z", floor_to_zero=True):
    """Rotate points into the Z-up frame the models were trained in and, optionally, shift so min z = 0.
    Returns (points_ml, offset_ml) so the result can be mapped back. The shift matters: see FAILURE-MODES in README."""
    P = np.asarray(points, dtype=np.float64) @ UP_AXES[up].T
    off = np.zeros(3)
    if floor_to_zero:
        off[2] = P[:, 2].min()
        P = P - off
    return P, off


def ml_to_source(points_ml, up="z", offset=None):
    P = np.asarray(points_ml, dtype=np.float64) + (0 if offset is None else offset)
    return P @ UP_AXES[up]


# ---------------------------------------------------------------------------------------------- formatting
def _f(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _vec(a):
    return " ".join(_f(v) for v in np.asarray(a, dtype=np.float64).ravel())


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _safe(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(name))


def _look_at(pos, target):
    """Orientation (axis-angle) for a Viewpoint at pos looking at target, Y up."""
    f = np.asarray(target, float) - np.asarray(pos, float)
    f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    R = np.c_[r, u, -f]  # columns: camera x, y, z in world
    ang = math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2)))
    if ang < 1e-9:
        return [0, 0, 1, 0]
    ax = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    n = np.linalg.norm(ax)
    ax = ax / n if n > 1e-9 else np.array([0, 1, 0])
    return list(ax) + [ang]


def _stage(P):
    """Viewpoint + Background + NavigationInfo framing the points (X3D, Y up)."""
    lo, hi = P.min(0), P.max(0)
    c, d = (lo + hi) / 2, float(np.linalg.norm(hi - lo))
    pos = c + np.array([0.55, 0.35, 1.15]) * d * 0.9
    return ('<NavigationInfo type="&quot;EXAMINE&quot; &quot;ANY&quot;" headlight="false"/>'
            '<Background skyColor="0.015 0.02 0.04"/>'
            '<Viewpoint DEF="VP_Overview" description="Overview" position="%s" orientation="%s" centerOfRotation="%s"/>'
            % (_vec(pos), _vec(_look_at(pos, c)), _vec(c)))


def _wrap(body, title, metas, profile="Interchange"):
    head = "".join('<meta name="%s" content="%s"/>' % (_esc(k), _esc(v)) for k, v in metas)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<X3D profile="%s" version="4.0">'
            '<head><meta name="title" content="%s"/><meta name="x3do3d.schema" content="%s"/>%s</head>'
            "<Scene>%s</Scene></X3D>\n") % (profile, _esc(title), SCHEMA, head, body)


# ---------------------------------------------------------------------------------------------- Open3D -> X3D
def pointcloud_to_x3d(points, colors=None, title="point cloud", metas=()):
    """points (N,3) Y-up X3D coordinates (no frame change here), colors (N,3) in 0..1 or None."""
    P = np.asarray(points)
    col = ""
    if colors is not None and len(colors):
        col = '<Color color="%s"/>' % _vec(np.clip(colors, 0, 1))
    body = '<Shape><PointSet><Coordinate point="%s"/>%s</PointSet></Shape>' % (_vec(P), col)
    return _wrap(body, title, [("x3do3d.points", len(P))] + list(metas))


def mesh_to_x3d(vertices, triangles, vertex_colors=None, title="mesh", metas=()):
    V = np.asarray(vertices)
    T = np.asarray(triangles, dtype=np.int64)
    idx = " ".join("%d %d %d -1" % tuple(t) for t in T)
    col = ""
    if vertex_colors is not None and len(vertex_colors):
        col = '<Color color="%s"/>' % _vec(np.clip(vertex_colors, 0, 1))
    body = ('<Shape><Appearance><Material diffuseColor="0.8 0.8 0.8"/></Appearance>'
            '<IndexedFaceSet solid="false" coordIndex="%s"%s><Coordinate point="%s"/>%s</IndexedFaceSet></Shape>'
            % (idx, ' colorPerVertex="true"' if col else "", _vec(V), col))
    return _wrap(body, title, [("x3do3d.vertices", len(V)), ("x3do3d.triangles", len(T))] + list(metas))


# ---------------------------------------------------------------------------------------------- X3D -> Open3D
def _floats(s):
    return np.fromstring(s.replace(",", " "), sep=" ", dtype=np.float64) if s and s.strip() else np.zeros(0)


def _rot_matrix(axis_angle):
    a = np.asarray(axis_angle, dtype=np.float64)
    n = np.linalg.norm(a[:3])
    if n < 1e-12 or abs(a[3]) < 1e-12:
        return np.eye(3)
    x, y, z = a[:3] / n
    c, s = math.cos(a[3]), math.sin(a[3])
    t = 1 - c
    return np.array([[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
                     [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
                     [t * x * z - s * y, t * y * z + s * x, t * z * z + c]])


def _transform_matrix(el):
    g = lambda k, d: _floats(el.get(k)) if el.get(k) else np.array(d, dtype=np.float64)
    T, C, S = g("translation", [0, 0, 0]), g("center", [0, 0, 0]), g("scale", [1, 1, 1])
    R, SR = _rot_matrix(g("rotation", [0, 0, 1, 0])), _rot_matrix(g("scaleOrientation", [0, 0, 1, 0]))
    M = np.eye(4)
    def mk(rot=np.eye(3), t=np.zeros(3), s=np.ones(3)):
        m = np.eye(4); m[:3, :3] = rot @ np.diag(s); m[:3, 3] = t; return m
    # T * C * R * SR * S * -SR * -C
    S4 = mk(SR) @ mk(np.eye(3), s=S) @ mk(SR.T)
    return mk(np.eye(3), T) @ mk(np.eye(3), C) @ mk(R) @ S4 @ mk(np.eye(3), -C)


def _walk(el, M, defs, out):
    tag = etree.QName(el).localname if isinstance(el.tag, str) else None
    if tag is None:
        return
    if el.get("USE") and tag not in ("Coordinate", "Color", "Normal"):
        el = defs.get(el.get("USE"), el)
        tag = etree.QName(el).localname
    if el.get("DEF"):
        defs[el.get("DEF")] = el
    if tag in ("Transform", "Group", "Switch", "Billboard", "Collision", "Anchor", "Scene", "LOD", "StaticGroup"):
        M2 = M @ _transform_matrix(el) if tag == "Transform" else M
        kids = list(el)
        if tag == "Switch":
            w = int(el.get("whichChoice", "-1"))
            kids = [k for i, k in enumerate(kids) if i == w] if w >= 0 else []
        for k in kids:
            _walk(k, M2, defs, out)
        return
    if tag == "Shape":
        geom = [k for k in el if isinstance(k.tag, str) and etree.QName(k).localname not in ("Appearance", "Metadata", "MetadataSet")]
        mat = el.find(".//{*}Material") if el.find(".//{*}Material") is not None else None
        for gnode in geom:
            out.append((gnode, M, mat))


def _node(el, name, defs):
    for k in el:
        if isinstance(k.tag, str) and etree.QName(k).localname == name:
            if k.get("USE"):
                return defs.get(k.get("USE"))
            return k
    return None


def read_x3d(src, o3d=True):
    """Parse X3D (a path, or an XML string) into lists of plain numpy geometry; with o3d=True returns Open3D objects.
    Returns {'pointclouds': [...], 'meshes': [...]}; unsupported geometry is counted in 'skipped'."""
    if isinstance(src, (str, Path)) and not str(src).lstrip().startswith("<"):
        root = etree.parse(str(src)).getroot()
    else:
        root = etree.fromstring(src.encode("utf-8") if isinstance(src, str) else src)
    defs = {}
    for e in root.iter():
        if isinstance(e.tag, str) and e.get("DEF"):
            defs.setdefault(e.get("DEF"), e)
    items = []
    scene = root.find("{*}Scene") if root.find("{*}Scene") is not None else root
    _walk(scene, np.eye(4), defs, items)
    pcs, meshes, skipped = [], [], {}
    for g, M, mat in items:
        tag = etree.QName(g).localname
        if g.get("USE"):
            g = defs.get(g.get("USE"), g)
            tag = etree.QName(g).localname
        c = _node(g, "Coordinate", defs)
        if c is None:
            skipped[tag] = skipped.get(tag, 0) + 1
            continue
        V = _floats(c.get("point")).reshape(-1, 3)
        V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3]
        col = _node(g, "Color", defs)
        C = _floats(col.get("color")).reshape(-1, 3) if col is not None else None
        if tag == "PointSet":
            pcs.append({"points": V, "colors": C})
        elif tag in ("IndexedFaceSet", "IndexedTriangleSet", "TriangleSet"):
            if tag == "TriangleSet":
                T = np.arange(len(V) // 3 * 3).reshape(-1, 3)
            elif tag == "IndexedTriangleSet":
                T = _floats(g.get("index")).astype(np.int64)
                T = T[: len(T) // 3 * 3].reshape(-1, 3)
            else:
                ci = _floats(g.get("coordIndex")).astype(np.int64)
                T, cur = [], []
                for i in ci:  # fan-triangulate each polygon
                    if i < 0:
                        T += [[cur[0], cur[j], cur[j + 1]] for j in range(1, len(cur) - 1)]
                        cur = []
                    else:
                        cur.append(int(i))
                if cur:
                    T += [[cur[0], cur[j], cur[j + 1]] for j in range(1, len(cur) - 1)]
                T = np.array(T, dtype=np.int64).reshape(-1, 3)
            if C is not None and len(C) != len(V):
                C = None  # per-face colours are not carried (counted, not guessed)
                skipped["per-face colour"] = skipped.get("per-face colour", 0) + 1
            meshes.append({"vertices": V, "triangles": T, "colors": C})
        else:
            skipped[tag] = skipped.get(tag, 0) + 1
    if o3d:
        import open3d as o3
        for d in pcs:
            p = o3.geometry.PointCloud(o3.utility.Vector3dVector(d["points"]))
            if d["colors"] is not None and len(d["colors"]) == len(d["points"]):
                p.colors = o3.utility.Vector3dVector(d["colors"])
            d["o3d"] = p
        for d in meshes:
            m = o3.geometry.TriangleMesh(o3.utility.Vector3dVector(d["vertices"]), o3.utility.Vector3iVector(d["triangles"]))
            if d["colors"] is not None:
                m.vertex_colors = o3.utility.Vector3dVector(d["colors"])
            d["o3d"] = m
    return {"pointclouds": pcs, "meshes": meshes, "skipped": skipped}


# ---------------------------------------------------------------------------------------------- Open3D-ML -> X3D
def _metadata_set(name, ref, items):
    """items: list of (name, kind, value) kind in string|integer|float."""
    kinds = {"string": "MetadataString", "integer": "MetadataInteger", "float": "MetadataFloat"}
    out = []
    for n, k, v in items:
        # X_ITE 16.7.1 treats a bare Metadata* node as containerField "value": a MetadataSet under a Group warned
        # "Unknown field 'value' in node class Group". So the outer set says containerField="metadata" and the children say "value".
        # MetadataString.value is an MFString, so the text is quoted. XSD 4.0 (x3d_mcp 4d433af) passed both mistakes.
        val = ('value="&quot;%s&quot;"' % _esc(str(v).replace("\\", "\\\\").replace('"', '\\"'))) if k == "string" else ('value="%s"' % (int(v) if k == "integer" else _f(float(v))))
        out.append('<%s containerField="value" name="%s" %s/>' % (kinds[k], _esc(n), val))
    return '<MetadataSet containerField="metadata" name="%s" reference="%s">%s</MetadataSet>' % (_esc(name), _esc(ref), "".join(out))


def _obb_lines(pts_x3d):
    """Wire box (IndexedLineSet) around points via Open3D's oriented bounding box; returns (xml, centre, extent) or None."""
    if len(pts_x3d) < 10:
        return None
    import open3d as o3
    pc = o3.geometry.PointCloud(o3.utility.Vector3dVector(np.asarray(pts_x3d, dtype=np.float64)))
    try:
        b = pc.get_oriented_bounding_box()
    except Exception:
        return None
    c = np.asarray(b.get_box_points())
    edges = [(0, 1), (0, 2), (0, 3), (1, 6), (1, 7), (2, 5), (2, 7), (3, 5), (3, 6), (4, 5), (4, 6), (4, 7)]  # Open3D box-corner topology
    idx = " ".join("%d %d -1" % e for e in edges)
    xml = ('<Shape><IndexedLineSet coordIndex="%s"><Coordinate point="%s"/></IndexedLineSet></Shape>' % (idx, _vec(c)))
    return xml, np.asarray(b.center), np.asarray(b.extent)


def confidence_color(s):
    """Cold (uncertain) to warm (confident): dark blue -> teal -> yellow. 0..1 in, rgb 0..1 out."""
    s = np.clip(np.asarray(s, dtype=np.float64), 0, 1)[:, None]
    lo, mid, hi = np.array([0.10, 0.12, 0.45]), np.array([0.10, 0.65, 0.65]), np.array([1.0, 0.90, 0.20])
    return np.where(s < 0.5, lo + (mid - lo) * (s * 2), mid + (hi - mid) * ((s - 0.5) * 2))


def segmentation_to_x3d(points_x3d, labels, class_names, class_colors=None, rgb=None, scores=None,
                        title="Open3D-ML semantic segmentation", metas=(), boxes=True, max_points=None, seed=0,
                        ignore=(), point_size=2.5):
    """points_x3d (N,3) already in X3D (Y up) coordinates; labels (N,) ints keyed by class_names {id: name};
    class_colors {id: '#rrggbb' or rgb 0..1}; rgb (N,3) 0..1 source colours; scores (N,) 0..1.
    Returns (xml, stats) where stats is per-class {count, share, mean_score, box_extent}."""
    P = np.asarray(points_x3d, dtype=np.float64)
    L = np.asarray(labels, dtype=np.int64)
    if max_points and len(P) > max_points:
        sel = np.sort(np.random.default_rng(seed).choice(len(P), max_points, replace=False))
        P, L = P[sel], L[sel]
        rgb = None if rgb is None else np.asarray(rgb)[sel]
        scores = None if scores is None else np.asarray(scores)[sel]
    n = len(P)
    cc = {}
    for k in class_names:
        v = (class_colors or {}).get(k)
        cc[k] = _hex_to_rgb(v) if isinstance(v, str) else (list(v) if v is not None else list(__import__("colorsys").hsv_to_rgb((k * 0.61803) % 1, 0.7, 0.95)))
    conf = confidence_color(scores) if scores is not None else None
    groups, stats = [], {}
    for k in sorted(class_names):
        if k in ignore:
            continue
        m = L == k
        cnt = int(m.sum())
        stats[class_names[k]] = {"id": int(k), "count": cnt, "share": cnt / n if n else 0.0,
                                  "mean_score": float(np.mean(scores[m])) if (scores is not None and cnt) else None}
        if cnt == 0:
            continue
        nm = _safe(class_names[k])
        coord = '<Coordinate DEF="c_%s" point="%s"/>' % (nm, _vec(P[m]))
        # lens 0 holds the Coordinate and the Appearance; later lenses USE them (X3D requires DEF before USE).
        ap0 = '<Appearance DEF="a_%s"><PointProperties pointSizeScaleFactor="%s" pointSizeMinValue="1" pointSizeMaxValue="8"/></Appearance>' % (nm, _f(point_size))
        apu = '<Appearance USE="a_%s"/>' % nm
        lens = ['<Shape>%s<PointSet>%s<Color color="%s"/></PointSet></Shape>' % (ap0, coord, _vec(np.tile(cc[k], (cnt, 1))))]
        if rgb is not None:
            lens.append('<Shape>%s<PointSet><Coordinate USE="c_%s"/><Color color="%s"/></PointSet></Shape>' % (apu, nm, _vec(np.asarray(rgb)[m])))
        if conf is not None:
            lens.append('<Shape>%s<PointSet><Coordinate USE="c_%s"/><Color color="%s"/></PointSet></Shape>' % (apu, nm, _vec(conf[m])))
        meta = [("classId", "integer", k), ("className", "string", class_names[k]), ("pointCount", "integer", cnt),
                ("share", "float", stats[class_names[k]]["share"]), ("colorHex", "string", "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in cc[k]))]
        if scores is not None:
            meta.append(("meanScore", "float", stats[class_names[k]]["mean_score"]))
        box = _obb_lines(P[m]) if boxes else None
        boxxml = ""
        if box:
            bx, c0, ex = box
            stats[class_names[k]]["box_extent"] = [round(float(x), 3) for x in sorted(ex)]
            boxxml = '<Switch DEF="box_%s" whichChoice="-1"><Group>%s</Group></Switch>' % (nm, bx)
        groups.append('<Switch DEF="vis_%s" whichChoice="0"><Group DEF="class_%s">%s'
                      '<Switch DEF="lens_%s" whichChoice="0">%s</Switch>%s</Group></Switch>'
                      % (nm, nm, _metadata_set("o3dml.class", REFERENCE, meta), nm, "".join(lens), boxxml))
    body = _stage(P) + "<Group DEF=\"segmentation\">%s</Group>" % "".join(groups)
    mt = [("x3do3d.points", n), ("x3do3d.classes", len([s for s in stats.values() if s["count"]])),
          ("x3do3d.lenses", "class" + (",rgb" if rgb is not None else "") + (",confidence" if conf is not None else ""))]
    return _wrap(body, title, mt + list(metas)), stats


def boxes_to_x3d(boxes, title="Open3D-ML 3D detections", metas=(), colors=None, text_size=0.5):
    """boxes: list of dict(center=[x,y,z] ML frame (Z up), size=[w,h,l] (x,y,z extents before yaw: l along x),
    yaw (radians about +z), label (str), confidence (0..1), id optional).  Written as Y-up X3D wire boxes with a
    Billboard label and a MetadataSet carrying the ML-frame numbers, so read_boxes() recovers them exactly."""
    out = []
    for i, b in enumerate(boxes):
        cx = ml_to_x3d(b["center"])
        sz = np.asarray(b["size"], dtype=np.float64)
        col = (colors or {}).get(b["label"], "#ffcc00")
        col = _hex_to_rgb(col) if isinstance(col, str) else col
        hx, hy, hz = sz / 2
        # unit box in the box's own frame, mapped to X3D axes (x, z->y, -y->z); yaw about ML z == X3D y
        corners = np.array([[sx * hx, sy * hy, sz_ * hz] for sx in (-1, 1) for sy in (-1, 1) for sz_ in (-1, 1)])
        c3 = ml_to_x3d(corners)
        idx = "0 1 3 2 0 4 5 7 6 4 -1 1 5 -1 3 7 -1 2 6 -1"
        yaw = float(b.get("yaw", 0.0))
        meta = [("label", "string", b["label"]), ("confidence", "float", b.get("confidence", 1.0)),
                ("mlCenter", "string", _vec(b["center"])), ("mlSize", "string", _vec(b["size"])), ("yaw", "float", yaw),
                ("frame", "string", "Open3D-ML Z-up, size=[x,y,z] before yaw")]
        out.append('<Transform DEF="box_%s" translation="%s" rotation="0 1 0 %s">%s'
                   '<Shape><Appearance><Material emissiveColor="%s" diffuseColor="0 0 0"/></Appearance>'
                   '<IndexedLineSet coordIndex="%s"><Coordinate point="%s"/></IndexedLineSet></Shape>'
                   '<Transform translation="0 %s 0"><Billboard axisOfRotation="0 0 0"><Shape><Appearance><Material diffuseColor="%s"/></Appearance>'
                   '<Text string="&quot;%s %d%%&quot;"><FontStyle size="%s" justify="&quot;MIDDLE&quot;"/></Text></Shape></Billboard></Transform></Transform>'
                   % (b.get("id", i), _vec(cx), _f(yaw), _metadata_set("o3dml.box", REFERENCE, meta), _vec(col), idx, _vec(c3),
                      _f(hz + 0.3), _vec(col), _esc(b["label"]), round(100 * b.get("confidence", 1.0)), _f(text_size)))
    return _wrap("<Group DEF=\"detections\">%s</Group>" % "".join(out), title,
                 [("x3do3d.boxes", len(boxes))] + list(metas))


def _mfs1(v):
    """First string of an MFString attribute value (quoted, with \\" and \\\\ escapes); a bare value is returned as is."""
    v = v.strip()
    if not v.startswith('"'):
        return v
    out, esc = [], False
    for ch in v[1:]:
        if esc:
            out.append(ch); esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            break
        else:
            out.append(ch)
    return "".join(out)


def read_boxes(src):
    root = etree.parse(str(src)).getroot() if not str(src).lstrip().startswith("<") else etree.fromstring(src.encode())
    boxes = []
    for ms in root.iter("{*}MetadataSet"):
        if ms.get("name") != "o3dml.box":
            continue
        d = {}
        for m in ms:
            d[m.get("name")] = _mfs1(m.get("value"))
        boxes.append({"label": d["label"], "confidence": float(d["confidence"]), "center": _floats(d["mlCenter"]).tolist(),
                      "size": _floats(d["mlSize"]).tolist(), "yaw": float(d["yaw"])})
    return boxes


def read_segmentation(src):
    """Recover per-class point sets from a scene segmentation_to_x3d wrote. Returns {class_name: {id, points, mean_score...}}."""
    root = etree.parse(str(src)).getroot() if not str(src).lstrip().startswith("<") else etree.fromstring(src.encode())
    out = {}
    for g in root.iter("{*}Group"):
        if not (g.get("DEF") or "").startswith("class_"):
            continue
        ms = g.find("{*}MetadataSet")
        meta = {m.get("name"): _mfs1(m.get("value")) for m in ms}
        co = g.find(".//{*}Coordinate")
        out[meta["className"]] = {"id": int(meta["classId"]), "count": int(meta["pointCount"]),
                                  "mean_score": float(meta["meanScore"]) if "meanScore" in meta else None,
                                  "points": _floats(co.get("point")).reshape(-1, 3)}
    return out


# ---------------------------------------------------------------------------------------------- Open3D-ML inference
S3DIS_NAMES = {0: "ceiling", 1: "floor", 2: "wall", 3: "beam", 4: "column", 5: "window", 6: "door", 7: "table",
               8: "chair", 9: "sofa", 10: "bookcase", 11: "board", 12: "clutter"}
S3DIS_COLORS = {0: "#4e79a7", 1: "#9c755f", 2: "#f28e2b", 3: "#b07aa1", 4: "#edc948", 5: "#76b7b2", 6: "#e15759",
                7: "#59a14f", 8: "#ff9da7", 9: "#af7aa1", 10: "#8cd17d", 11: "#bab0ac", 12: "#7f7f7f"}


def run_randlanet_s3dis(points_ml, rgb01, ckpt, cfg_path, device="cpu"):
    """CPU inference with Open3D-ML's RandLA-Net (S3DIS). points_ml must be Z up with floor near 0.
    Returns (labels, confidence) where confidence = the winning class's share of that point's score vector (0..1; NOT calibrated)."""
    import open3d.ml as _ml
    import open3d.ml.torch as ml3d
    cfg = _ml.utils.Config.load_from_file(str(cfg_path))
    model = ml3d.models.RandLANet(**cfg.model)
    pipe = ml3d.pipelines.SemanticSegmentation(model, dataset=None, device=device, **cfg.pipeline)
    pipe.load_ckpt(ckpt_path=str(ckpt))
    r = pipe.run_inference({"point": np.asarray(points_ml, np.float32), "feat": np.asarray(rgb01, np.float32) * 255.0,
                            "label": np.zeros(len(points_ml), np.int32)})
    # predict_scores is the pipeline's smoothed running average (it starts at zero and is damped each pass), so its rows
    # do not sum to 1 (max row-wise value was 0.07 in the first run). Renormalise per point: confidence = max / sum.
    p = np.asarray(r["predict_scores"], dtype=np.float64)
    return np.asarray(r["predict_labels"]), p.max(axis=1) / np.maximum(p.sum(axis=1), 1e-12)
