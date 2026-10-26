#!/bin/bash
# usage: guard.sh <agent_script.py> <outdir> <X3D40|X3D41> [--data-colour]
set -u
W="$(cd "$(dirname "$0")" && pwd)"; ROOT="$W/.."
export BLENDER_USER_RESOURCES="$W/bl_user" GUARD_WORK="$W"
mkdir -p "$2"
"$ROOT/../v/bin/python" -I "$W/bl_phase.py" --src "$ROOT/x3d_mcp/src" --addon "$ROOT/x3d-blender-io/source" --script "$1" --out "$2" --x3d-version "$3" ${4:-} 2>&1 | grep -E "bl_phase done|Traceback|Error" 
"$ROOT/venv/bin/python" -I "$W/gate.py" "$ROOT/x3d_mcp/src" "$2"
