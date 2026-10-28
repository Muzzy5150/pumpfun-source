#!/usr/bin/env python3
"""calib.py <module.ll|stubbed.ll> <fn regex> <linked unstripped.so> [llc flags...]: llc one function and diff it
against the same function in a linked build (masked call/lddw immediates), to calibrate the llc pipeline."""
import difflib, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, '/Users/shawwalters/Documents/Codex/2026-10-24/claude-pump-work/harness')
import irtool
from score import sections, body, candidate_functions
ll, pat, so = sys.argv[1:4]; flags = sys.argv[4:]
b = Path(so).read_bytes(); cs = sections(b)
f = [x for x in candidate_functions(so) if __import__('re').search(pat, x[2])]
assert len(f) == 1, f
cand = body(b, cs, f[0][0], f[0][1])
obj = Path(ll).with_suffix('.calib.o')
irtool.llc(ll, obj, flags)
sec, code = irtool.obj_function(obj, pat)
o = irtool.masked(cand); c = irtool.masked(code)
sm = difflib.SequenceMatcher(None, o, c, autojunk=False)
print(f'llc {len(code)} B vs linked {len(cand)} B  ratio={sm.ratio():.4f}  flags={flags}')
for t, i1, i2, j1, j2 in sm.get_opcodes():
    if t != 'equal':
        print('  ', t, i1, i2, j1, j2)
