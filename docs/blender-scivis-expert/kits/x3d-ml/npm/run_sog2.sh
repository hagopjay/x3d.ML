#!/bin/bash
cd /tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/x3d-ml/npm
for H in 1 2; do
  s=$(date +%s.%N)
  timeout 1500 node node_modules/.bin/splat-transform -w -g cpu synth133k.ply -H $H conv/synth133k_h$H.sog > conv/sog_h$H.log 2>&1
  rc=$?; e=$(date +%s.%N); echo "H=$H sog rc=$rc $(echo "$e - $s" | bc)s" >> conv/sog_timing2.txt
done
