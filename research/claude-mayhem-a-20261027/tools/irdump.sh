#!/bin/bash
# irdump.sh VARIANT LABEL PASS FUNC : rebuild variant tree with IR printing after PASS for FUNC (mangled)
L=/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/mayhem-a
v=$1; label=$2; pass=$3; fn=$4
cd $L && rsync -rlpgoD --checksum --delete b/$v/ b/work-mixed/ && python3 out/tools/mbuild.py $label b/work-mixed --sdk mixed --linker qualified --target-name mixed --clean '' --extra-rustc-json "[\"--remap-path-prefix=src/account_wrapper.rs=src/account_wrapper.rs\",\"-Cllvm-args=-print-after=$pass\",\"-Cllvm-args=-filter-print-funcs=$fn\"]" > /dev/null 2>&1
python3 - "$L/out/builds/$label/stderr" "$L/out/builds/$label/ir.ll" <<'PY'
import sys
lines=open(sys.argv[1]).read().splitlines()
out=[];on=False
for l in lines:
    if 'IR Dump After' in l or '# *** IR Dump' in l: on=True
    if on: out.append(l)
open(sys.argv[2],'w').write('\n'.join(out)+'\n')
print(len(out),'lines ->',sys.argv[2])
PY
