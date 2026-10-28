#!/bin/bash
# usage: irb.sh LABEL ROOT OUTNAME [TARGET] -> builds ROOT with --emit=llvm-ir,link, copies IR to o84/out/OUTNAME.ll
set -e
MW=/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work
L=$MW/mayhem-b
T=${4:-o84-ir}
rm -rf $L/out/builds/$1
MAYHEM_ROOT_RUSTC_ARGS_JSON=${IRB_ARGS:-'["--emit=llvm-ir,link"]'} LANE_CLEAN_ANCHOR=0 python3 $MW/sbf_lock.py --slots 6 --name sbf -- python3 $L/build/build_lane.py $1 $2 $T > $MW/o84/out/$1.log 2>&1
cp $L/target/$T/sbpf-solana-solana/release/deps/mayhem_recovered.ll $MW/o84/out/$3.ll
echo "IR -> $MW/o84/out/$3.ll"
