"""Show an aligned normalized diff of an original window vs a candidate function."""
import sys, difflib, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pm
ap = argparse.ArgumentParser()
ap.add_argument('orig', type=lambda s: int(s, 0))
ap.add_argument('cand', type=lambda s: int(s, 0))
ap.add_argument('--candidate', default=str(pm.WT / 'repro/pump/main-contract-round26-20261027/unstripped.so'))
ap.add_argument('--obytes', type=int, default=None)
ap.add_argument('--cbytes', type=int, default=None)
ap.add_argument('--context', type=int, default=2)
ap.add_argument('--all', action='store_true')
a = ap.parse_args()
ob = pm.ORIG.read_bytes(); cb = Path(a.candidate).read_bytes()
osec, csec = pm.sections(ob), pm.sections(cb)
inv = pm.read_json(pm.WT / 'repro/pump/main-contract-round26-20261027/inventory.json.gz')
on = a.obytes or next(w['bytes'] for w in inv['windows'] if w['start'] == a.orig)
if a.cbytes: cn = a.cbytes
else:
    cn = next(n for s, n, _ in pm.candidate_functions(a.candidate) if s == a.cand)
oraw = pm.body(ob, osec, a.orig, on); craw = pm.body(cb, csec, a.cand, cn)
onorm = pm.normalize(oraw, a.orig, osec)[0]; cnorm = pm.normalize(craw, a.cand, csec)[0]
od = pm.disasm(pm.ORIG, a.orig, on); cd = pm.disasm(Path(a.candidate), a.cand, cn)
# map address->text
odt = {x[0]: x[1] for x in od}; cdt = {x[0]: x[1] for x in cd}
os_ = pm.slots(onorm); cs_ = pm.slots(cnorm)
sm = difflib.SequenceMatcher(None, os_, cs_, autojunk=False)
print(f'orig {a.orig:#x} {on}B vs cand {a.cand:#x} {cn}B ratio={sm.ratio():.4f} rawequal={oraw==craw} normequal={onorm==cnorm}')
nd = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        if a.all:
            for k in range(i2 - i1):
                print(f'   {(i1+k)*8:5d} {odt.get(a.orig+(i1+k)*8,""):45s} | {cdt.get(a.cand+(j1+k)*8,"")}')
        else:
            n = i2 - i1
            if n > 2 * a.context:
                for k in range(a.context):
                    print(f'   {(i1+k)*8:5d} {odt.get(a.orig+(i1+k)*8,""):45s} | {cdt.get(a.cand+(j1+k)*8,"")}')
                print(f'   ... {n-2*a.context} equal slots ...')
                for k in range(n - a.context, n):
                    print(f'   {(i1+k)*8:5d} {odt.get(a.orig+(i1+k)*8,""):45s} | {cdt.get(a.cand+(j1+k)*8,"")}')
            else:
                for k in range(n):
                    print(f'   {(i1+k)*8:5d} {odt.get(a.orig+(i1+k)*8,""):45s} | {cdt.get(a.cand+(j1+k)*8,"")}')
        continue
    nd += 1
    L = max(i2 - i1, j2 - j1)
    for k in range(L):
        ot = odt.get(a.orig + (i1 + k) * 8, '') if i1 + k < i2 else ''
        ct = cdt.get(a.cand + (j1 + k) * 8, '') if j1 + k < j2 else ''
        print(f'{tag[0].upper()}  {(i1+k)*8 if i1+k<i2 else "":>5} {ot:45s} | {ct}')
print('diff blocks', nd)
