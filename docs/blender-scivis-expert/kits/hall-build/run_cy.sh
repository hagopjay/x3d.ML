#!/bin/bash
# usage: run_cy.sh <bridge_dir_name> <out_name> [extra args]
S=/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/hall-build
BR=$1; OUT=$2; shift 2
export TMPDIR=$S/tmp; mkdir -p $TMPDIR $S/out
cd $S
$S/../v/bin/python -I $S/src/cycles_hall.py --bridge $S/$BR/source --x3d $S/hall17d/frozen_01_threshold.x3d --camera ViewThreshold \
  --out $S/out/$OUT.png --res 480 360 --samples 32 --device CPU --lamp-blockers triplet --cube-light 0.65 --cube-lamp-light 0.9 \
  --cube-haze 0.008 --lamp-direct --twilight-bounces 0 --lampglass-light off --lampglass-glow 1.0 --lampglass-tint --shadow-fill 0.06 "$@" > $S/out/$OUT.log 2>&1
echo "exit $?" >> $S/out/$OUT.log
