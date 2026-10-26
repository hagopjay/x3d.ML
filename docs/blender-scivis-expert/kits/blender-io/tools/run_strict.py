import sys, runpy, os
S = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io"
sys.path.append(S + "/x3dpkg")
os.environ["X3D_STRICT_VALIDATION"] = "1"
import x3d.x3d
print("[strict] x3d package", getattr(x3d.x3d, "__file__", "?"))
sys.argv = [S + "/repo/.github/scripts/run_tests_in_blender.py"]
runpy.run_path(sys.argv[0], run_name="__main__")
