#!/bin/bash
# mirdump.sh VARIANT LABEL FILTER : rebuild variant with -Zdump-mir=FILTER into out/builds/LABEL/mir
L=/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/mayhem-a
v=$1; label=$2; filt=$3
mkdir -p $L/out/mirtmp-$label
cd $L && rsync -rlpgoD --checksum --delete b/$v/ b/work-mixed/ && python3 out/tools/mbuild.py $label b/work-mixed --sdk mixed --linker qualified --target-name mixed --clean '' --extra-rustc-json "[\"--remap-path-prefix=src/account_wrapper.rs=src/account_wrapper.rs\",\"-Zdump-mir=$filt\",\"-Zdump-mir-dir=$L/out/mirtmp-$label\"]" > /dev/null 2>&1
mv $L/out/mirtmp-$label $L/out/builds/$label/mir; ls $L/out/builds/$label/mir | head
