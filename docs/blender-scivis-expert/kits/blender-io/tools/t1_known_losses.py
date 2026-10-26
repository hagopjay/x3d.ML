import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
register()
import swatch_book, scene_fixture, hanim_fixture, splat_fixture
cases = {
 "swatch": (lambda d: swatch_book.build_swatch_book(texture_dir=d), "X3D40", dict(use_normals=True)),
 "scene": (lambda d: scene_fixture.build_scene_fixture(), "X3D40", dict(use_hierarchy=True, use_animation=True)),
 "hanim": (lambda d: hanim_fixture.build_hanim_fixture(), "X3D40", dict(use_animation=True)),
 "splat": (lambda d: splat_fixture.build_splat_fixture(count=40), "X3D41", {}),
}
for name, (build, ver, kw) in cases.items():
    reset(); d = str(TMP / name); os.makedirs(d, exist_ok=True)
    build(d)
    invs = []
    for g in range(3):
        p = f"{d}/{name}_{g}.x3d"
        r = exp(p, ver, **kw); assert r == {"FINISHED"}, r
        invs.append(inventory(p))
        reset(); imp(p)
    a, b, c = invs
    print("==", name, "gen1==gen2 fixed point (gen2==gen3):", b == c)
    for t in sorted(set(a) | set(b)):
        if a[t] != b[t]:
            print(f"   {t}: gen0->{a[t]}  gen1->{b[t]}")
