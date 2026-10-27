"""Aligned diff on disassembly text with r10 frame offsets masked (reveals structural diffs)."""
import sys, re, difflib, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pm
ap = argparse.ArgumentParser(); ap.add_argument('orig', type=lambda s: int(s, 0)); ap.add_argument('osize', type=lambda s: int(s, 0))
ap.add_argument('cand', type=lambda s: int(s, 0)); ap.add_argument('csize', type=lambda s: int(s, 0)); ap.add_argument('--candidate', required=True)
ap.add_argument('--context', type=int, default=2)
a = ap.parse_args()
od = pm.disasm(pm.ORIG, a.orig, a.osize); cd = pm.disasm(Path(a.candidate), a.cand, a.csize)
def norm(t):
    t = re.sub(r'\[r10 - 0x[0-9a-f]+\]', '[r10-X]', t)
    t = re.sub(r'(add64 r\d+, )-0x[0-9a-f]+', r'\1-X', t)
    t = re.sub(r'call -?0x[0-9a-f]+', 'call F', t)
    t = re.sub(r'lddw (r\d+), 0x[0-9a-f]+', r'lddw \1, P', t)
    t = re.sub(r'<[^>]*>', '', t)
    t = re.sub(r'([+-])0x[0-9a-f]+ *$', r'\1J', t) if t.startswith('j') else t
    return t
on = [norm(t) for _, t in od]; cn = [norm(t) for _, t in cd]
sm = difflib.SequenceMatcher(None, on, cn, autojunk=False)
print('ratio', round(sm.ratio(), 4), len(on), len(cn))
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal': continue
    L = max(i2 - i1, j2 - j1)
    for k in range(L):
        ot = f'{od[i1+k][0]-a.orig:5d} {od[i1+k][1]}' if i1 + k < i2 else ''
        ct = f'{cd[j1+k][0]-a.cand:5d} {cd[j1+k][1]}' if j1 + k < j2 else ''
        print(f'{tag[0].upper()} {ot:55s} | {ct}')
    print('-')
