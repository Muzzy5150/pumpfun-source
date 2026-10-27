#!/bin/bash
# usage: trial.sh <name> <source-dir relative to worktree> [packet]
# Builds under the shared sbf slot lock with the frontier recipe, then measures.
set -euo pipefail
SP=/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad
L=$SP/lanes/pump-hi
WT=$L/wt
name=$1; src=$2
packet=${3:-$WT/repro/pump/main-contract-round36-20261027}
out=$WT/work/$name
rm -rf "$out"
cd "$WT"
python3 $SP/sbf_lock.py --slots 6 --name sbf -- python3 $WT/research/claude-pump-hi-20261027/tools/build.py \
  --packet "$packet" --source-directory "$WT/$src" --registry-home ~/.cargo --output "$out" \
  --dependency-cache $L/out/depcache > $L/out/$name.build.log 2>&1 || { echo "BUILD FAILED: see $L/out/$name.build.log and $out/build.log"; grep -m20 -E "^error|error\[" "$out/build.log" 2>/dev/null || true; exit 1; }
python3 $WT/research/claude-pump-hi-20261027/tools/measure.py --packet "$packet" --candidate "$out/unstripped.so" --output $L/out/$name.measure.json
shasum -a 256 "$out/candidate.so" "$out/unstripped.so"
