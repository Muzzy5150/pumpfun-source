#!/usr/bin/env python3
"""usage: hunks.py SYMBOLS.so|OBJ.o [lo hi] [maxhunks] -- masked diff hunks of sell_v2_handler vs original O0084."""
import sys, difflib
sys.path.insert(0, '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/o84/tools')
import irx, objsec
p = sys.argv[1]
if p.endswith('.o'):
    secs = objsec.sections(p); key = [k for k in secs if irx.PAT in k and k.startswith('.text')][0]; code = secs[key]
else:
    code = irx.elf_code(p)
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3]) if len(sys.argv) > 3 else 1 << 30
mh = int(sys.argv[4]) if len(sys.argv) > 4 else 200
print('score', irx.score(code))
irx.show_code(code, maxhunks=mh, context=2, lo=lo, hi=hi)
