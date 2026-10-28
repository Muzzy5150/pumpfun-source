#!/usr/bin/env python3
"""usage: regions.py SYMBOLS.so|OBJ.o -- per-hunk masked diff sizes (orig offset, cand offset, -lines, +lines) and region totals."""
import sys, difflib
sys.path.insert(0, '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/o84/tools')
import irx, objsec, sbfdis
p = sys.argv[1]
if p.endswith('.o'):
    secs = objsec.sections(p); key = [k for k in secs if irx.PAT in k and k.startswith('.text')][0]; code = secs[key]
else:
    code = irx.elf_code(p)
a = irx.ORIG_LINES; b = irx.masked_lines(code, 0)
oc = irx.O.b[irx.W[1]:irx.W[2]]
apc = [pc for pc, raw in objsec.insns(oc)]
bpc = [pc for pc, raw in objsec.insns(code)]
sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
reg = {}
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal': continue
    o = apc[i1] if i1 < len(apc) else 99999
    n = max(i2 - i1, j2 - j1)
    k = o // 1000 * 1000
    reg[k] = reg.get(k, 0) + n
    if len(sys.argv) > 2: print(f'O+{o:6d} C+{bpc[j1] if j1 < len(bpc) else 99999:6d} -{i2-i1:3d} +{j2-j1:3d} {tag}')
print('score', irx.score(code))
print(' '.join(f'{k}:{v}' for k, v in sorted(reg.items())))
