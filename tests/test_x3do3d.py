"""Tests for o3d_bridge/x3do3d.py. Geometry tests need numpy, lxml, open3d; the model test needs open3d.ml.torch plus a
checkpoint (X3DO3D_CKPT, X3DO3D_CFG) and is skipped otherwise."""
import os
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")  # CI installs only lxml and friends; these tests need numpy and open3d

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "o3d_bridge"))
import x3do3d as B  # noqa: E402

o3d = pytest.importorskip("open3d")
RNG = np.random.default_rng(7)


def test_frames_are_proper_rotations_and_invert():
    for M in (B._X3D_TO_ML, B._ML_TO_X3D, *B.UP_AXES.values()):
        assert np.isclose(np.linalg.det(M), 1.0)
    p = RNG.normal(size=(50, 3))
    assert np.allclose(B.ml_to_x3d(B.x3d_to_ml(p)), p)
    assert np.allclose(B.x3d_to_ml([[0, 1, 0]]), [[0, 0, 1]])  # X3D up (+y) is ML up (+z)


def test_camera_frame_up_is_minus_y():
    P, off = B.ml_frame_from_source(np.array([[0, -1, 0], [0, 2, 0.5]]), "-y")  # y down: -1 is higher than 2
    assert P[0, 2] > P[1, 2] and P[:, 2].min() == 0
    assert np.allclose(B.ml_to_source(P, "-y", off), [[0, -1, 0], [0, 2, 0.5]])


def test_pointcloud_roundtrip():
    p, c = RNG.uniform(-5, 5, (500, 3)), RNG.uniform(0, 1, (500, 3))
    rd = B.read_x3d(B.pointcloud_to_x3d(p, c))
    q = rd["pointclouds"][0]
    assert np.abs(q["points"] - p).max() <= 5e-4 + 1e-12 and np.abs(q["colors"] - c).max() <= 5e-4 + 1e-12
    assert len(rd["pointclouds"][0]["o3d"].points) == 500


def test_mesh_roundtrip_with_quads_and_transform_stack():
    x3d = ('<X3D profile="Interchange" version="4.0"><Scene>'
           '<Transform translation="1 2 3" rotation="0 0 1 1.5707963267948966" scale="2 2 2">'
           '<Shape><IndexedFaceSet coordIndex="0 1 2 3 -1"><Coordinate DEF="q" point="0 0 0 1 0 0 1 1 0 0 1 0"/></IndexedFaceSet></Shape></Transform>'
           '<Shape><PointSet><Coordinate USE="q"/></PointSet></Shape></Scene></X3D>')
    rd = B.read_x3d(x3d)
    m = rd["meshes"][0]
    assert len(m["triangles"]) == 2                       # quad fan-triangulated
    # (1,0,0) scaled 2 -> (2,0,0), rotated +90 deg about z -> (0,2,0), translated -> (1,4,3)
    assert np.allclose(m["vertices"][1], [1, 4, 3], atol=1e-9)
    assert len(rd["pointclouds"][0]["points"]) == 4       # DEF/USE of Coordinate resolved
    assert len(rd["meshes"][0]["o3d"].triangles) == 2


def test_unsupported_geometry_is_counted_not_dropped_silently():
    rd = B.read_x3d('<X3D version="4.0"><Scene><Shape><Sphere/></Shape></Scene></X3D>', o3d=False)
    assert rd["skipped"] == {"Sphere": 1} and not rd["pointclouds"]


def test_switch_hides_unchosen_children():
    x3d = ('<X3D version="4.0"><Scene><Switch whichChoice="1"><Shape><PointSet><Coordinate point="0 0 0"/></PointSet></Shape>'
           '<Shape><PointSet><Coordinate point="1 1 1 2 2 2"/></PointSet></Shape></Switch></Scene></X3D>')
    assert [len(p["points"]) for p in B.read_x3d(x3d, o3d=False)["pointclouds"]] == [2]


def _seg():
    P = RNG.uniform(0, 3, (900, 3))
    L = RNG.integers(0, 3, 900)
    names, cols = {0: "floor", 1: "wall", 2: "odd name&<>"}, {0: "#112233", 1: "#aabbcc", 2: "#ff0000"}
    return P, L, B.segmentation_to_x3d(P, L, names, cols, rgb=RNG.uniform(0, 1, (900, 3)), scores=RNG.uniform(0, 1, 900))


def test_segmentation_roundtrip_counts_and_positions():
    P, L, (xml, st) = _seg()
    seg = B.read_segmentation(xml)
    assert sum(s["count"] for s in seg.values()) == 900
    for k, name in ((0, "floor"), (1, "wall"), (2, "odd name&<>")):
        assert seg[name]["count"] == int((L == k).sum()) == len(seg[name]["points"])
        assert np.abs(seg[name]["points"] - P[L == k]).max() <= 5e-4 + 1e-12
    assert st["floor"]["mean_score"] is not None and abs(st["floor"]["share"] + st["wall"]["share"] + st["odd name&<>"]["share"] - 1) < 1e-12


def test_segmentation_scene_is_xsd_valid_when_validator_present():
    fork = os.environ.get("X3D_MCP_PATH")
    if not fork:
        pytest.skip("set X3D_MCP_PATH to an x3d_mcp checkout")
    sys.path.insert(0, str(Path(fork) / "src"))
    from validation.validate import validate_xml
    _, _, (xml, _) = _seg()
    r = validate_xml(xml, "4.0")
    assert r["valid"], r["errors"]
    boxes = B.boxes_to_x3d([dict(center=[1, 2, 3], size=[4, 2, 1.5], yaw=0.3, label="car", confidence=0.9)])
    assert validate_xml(boxes, "4.0")["valid"]


def test_box_roundtrip_exact_to_rounding():
    boxes = [dict(center=[10.5, -2.25, 0.8], size=[4.1, 1.8, 1.6], yaw=0.7, label="Car", confidence=0.93),
             dict(center=[3, 4, 0.9], size=[0.6, 0.7, 1.8], yaw=-1.2, label="Pedestrian", confidence=0.51)]
    back = B.read_boxes(B.boxes_to_x3d(boxes))
    assert [b["label"] for b in back] == ["Car", "Pedestrian"]
    for a, b in zip(boxes, back):
        assert np.allclose(a["center"], b["center"], atol=5e-4) and np.allclose(a["size"], b["size"], atol=5e-4)
        assert abs(a["yaw"] - b["yaw"]) < 5e-4 and abs(a["confidence"] - b["confidence"]) < 5e-4


def test_box_corner_world_position_matches_ml_frame():
    # a car 4 long (ML x), 2 wide (ML y), 1.5 tall (ML z), yaw 0, centre (10,0,1): its top is at ML z 1.75 -> X3D y 1.75
    xml = B.boxes_to_x3d([dict(center=[10, 0, 1], size=[4, 2, 1.5], yaw=0.0, label="Car", confidence=1.0)])
    from lxml import etree
    root = etree.fromstring(xml.encode())
    tr = root.find(".//{*}Transform")
    assert np.allclose(B._floats(tr.get("translation")), [10, 1, 0])
    pts = B._floats(root.find(".//{*}IndexedLineSet/{*}Coordinate").get("point")).reshape(-1, 3)
    assert np.isclose(pts[:, 1].max(), 0.75) and np.isclose(pts[:, 0].max(), 2) and np.isclose(pts[:, 2].max(), 1)


def test_confidence_color_monotone_ends():
    c = B.confidence_color([0, 0.5, 1])
    assert c[0, 2] > c[0, 0] and c[2, 0] > c[2, 2]  # cold end blue, warm end yellow


@pytest.mark.skipif(not (os.environ.get("X3DO3D_CKPT") and os.environ.get("X3DO3D_CFG")), reason="needs Open3D-ML checkpoint")
def test_randlanet_end_to_end_on_a_synthetic_room():
    pytest.importorskip("open3d.ml.torch")
    # floor + two walls: the floor must come back mostly 'floor'
    g = np.linspace(0, 4, 90)
    xx, yy = np.meshgrid(g, g)
    floor = np.c_[xx.ravel(), yy.ravel(), np.zeros(xx.size)]
    wall = np.c_[xx.ravel(), np.zeros(xx.size), np.tile(np.linspace(0, 2.6, 90), 90)]
    P = np.vstack([floor, wall])
    col = np.vstack([np.tile([0.5, 0.4, 0.3], (len(floor), 1)), np.tile([0.9, 0.9, 0.85], (len(wall), 1))])
    lab, conf = B.run_randlanet_s3dis(P, col, os.environ["X3DO3D_CKPT"], os.environ["X3DO3D_CFG"])
    assert lab.shape == (len(P),) and 0 <= conf.min() and conf.max() <= 1.0 + 1e-9
    assert (lab[: len(floor)] == 1).mean() > 0.5


def test_metadata_children_are_x_ite_clean():
    """Regression: X_ITE warned 'Unknown field value in node class Group' (a MetadataSet under a Group needs containerField="metadata", its children "value")
    and 'MFString ... separate each string with double quotation marks'; XSD 4.0 passed both. Found by rendering, 25 Nov."""
    xml = B.boxes_to_x3d([dict(center=[0, 0, 0], size=[1, 1, 1], yaw=0, label='say "hi"', confidence=1)])
    from lxml import etree
    root = etree.fromstring(xml.encode())
    assert all(m.get("containerField") == "metadata" for m in root.iter("{*}MetadataSet"))
    for m in root.iter("{*}MetadataString", "{*}MetadataInteger", "{*}MetadataFloat"):
        assert m.get("containerField") == "value"
    for m in root.iter("{*}MetadataString"):
        assert m.get("value").startswith('"') and m.get("value").endswith('"')
    assert B.read_boxes(xml)[0]["label"] == 'say "hi"'
