#!/bin/bash
S=/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/hall-build
SCRIPT=$1; BR=$2; OUT=$3
export TMPDIR=$S/tmp
$S/../v/bin/python -I $S/src/$SCRIPT --bridge $S/$BR/source --x3d $S/hall18b/frozen_f0.x3d --camera FilmCamera --out $S/out/$OUT.png --res 480 360 --samples 32 --device CPU \
  --lamp-blockers triplet --cube-light 0.65 --cube-lamp-light 0.9 --cube-haze 0.008 --lamp-direct --twilight-bounces 0 --lampglass-light off --lampglass-glow 1.0 --lampglass-tint --shadow-fill 0.06 > $S/out/$OUT.log 2>&1
grep -E "RENDERSTAT|Traceback|Error" $S/out/$OUT.log | cut -c1-160
