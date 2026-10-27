#!/bin/bash
# usage: mdiff2.sh LABEL WID [maxlines] [maskregs]  -- stack-masked diff
L=/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/mayhem-b
cd $L/build && python3 -c "
import sbfdis, winreport
O=winreport.O
w=[x for x in winreport.W if x[0]=='$2'][0]
C=sbfdis.elf('$L/out/builds/$1/symbols.so')
cf=sbfdis.funcs(C)
a=[a for a,(b,n) in cf.items() if w[3] in n][0]
sbfdis.diff_masked(O,w[1],w[2],C,a,cf[a][0],context=1,maxlines=${3:-300},mask_regs=${4:-False})
"
