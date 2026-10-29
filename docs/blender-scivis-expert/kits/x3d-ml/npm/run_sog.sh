#!/bin/bash
cd /tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/x3d-ml/npm
for H in 0 3; do
  s=$(date +%s.%N)
  if [ "$H" = "3" ]; then timeout 1700 node node_modules/.bin/splat-transform -w -g cpu synth133k.ply conv/synth133k.sog > conv/sog_h3.log 2>&1; else timeout 1700 node node_modules/.bin/splat-transform -w -g cpu synth133k.ply -H 0 conv/synth133k_h0.sog > conv/sog_h0.log 2>&1; fi
  e=$(date +%s.%N); echo "H=$H sog rc=$? $(echo "$e - $s" | bc)s" >> conv/sog_timing.txt
done
