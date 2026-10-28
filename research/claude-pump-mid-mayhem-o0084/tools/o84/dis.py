#!/usr/bin/env python3
"""usage: dis.py (orig|SYMBOLS.so|OBJ.o) lo hi -- disassemble sell_v2_handler between byte offsets."""
import sys
sys.path.insert(0, '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/o84/tools')
import irx, objsec, sbfdis
p = sys.argv[1]
if p == 'orig':
    code = irx.O.b[irx.W[1]:irx.W[2]]
elif p.endswith('.o'):
    secs = objsec.sections(p); key = [k for k in secs if irx.PAT in k and k.startswith('.text')][0]; code = secs[key]
else:
    code = irx.elf_code(p)
lo, hi = int(sys.argv[2]), int(sys.argv[3])
for pc, raw in objsec.insns(code):
    if lo <= pc < hi:
        print(f'{pc:6d}  {sbfdis.decode(code, None, pc, pc + len(raw), None, None)[0]["text"]}')
