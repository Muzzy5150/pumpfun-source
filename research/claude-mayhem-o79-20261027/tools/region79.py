#!/usr/bin/env python3
"""Diff summary by original-offset region (regs+fp masked) for a built label or .bin."""
import sys, os, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llc79, mark79
def summary(code, step=1000, regs=True):
    ta = llc79.texts(llc79.ORIG); tb = llc79.texts(code)
    a = [llc79.norm(t, regs) for _, _, t in ta]; b = [llc79.norm(t, regs) for _, _, t in tb]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    buckets = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal': continue
        o1 = ta[i1][0] if i1 < len(ta) else len(llc79.ORIG)
        k = o1 // step * step
        x = buckets.setdefault(k, [0, 0]); x[0] += i2 - i1; x[1] += j2 - j1
    return buckets
if __name__ == '__main__':
    step = int(os.environ.get('STEP', '1000')); regs = os.environ.get('REGS', '1') == '1'
    for lab in sys.argv[1:]:
        c = mark79.code_of(lab)
        bk = summary(c, step, regs)
        print(lab, ' '.join(f'{k}:{v[0]}/{v[1]}' for k, v in sorted(bk.items())))
