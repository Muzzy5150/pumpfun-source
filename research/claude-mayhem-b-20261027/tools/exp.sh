#!/bin/bash
# usage: exp.sh LABEL [ROOT] [TARGET]  -- build (root only), measure, window report
SP=/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad
L=$SP/lanes/mayhem-b; B=$L/build
label=$1; root=${2:-$B/roots/work}; tgt=${3:-main}
cd $L && LANE_CLEAN_ANCHOR=0 python3 $SP/sbf_lock.py --slots 6 --name sbf -- python3 $B/build_lane.py $label $root $tgt > $L/out/builds/$label.log 2>&1
rc=$?
if [ $rc -ne 0 ]; then echo "BUILD FAILED rc=$rc"; grep -E "^error|^warning: unused" -A6 $L/out/builds/$label/stderr | head -60; exit 1; fi
python3 $B/measure.py $L/out/builds/$label/symbols.so --json $L/out/builds/$label/measure.json > /dev/null
python3 -c "
import json,sys; d=json.load(open('$L/out/builds/$label/measure.json'))
print('statuses',d['statuses'],'unmatched_bytes',d['unmatched_window_bytes'])
print('counts',d['counts'])
for k in ['gains','body_losses','raw_gains','raw_losses','edge_losses','source_losses','source_gains']:
  if d[k]: print(k, d[k] if len(str(d[k]))<800 else str(d[k])[:800])
print('no_losses',d['no_losses'],'text',d['candidate_text_bytes'],'funcs',d['candidate_functions'])
"
python3 $B/winreport.py $L/out/builds/$label/symbols.so
