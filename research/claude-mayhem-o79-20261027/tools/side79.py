#!/usr/bin/env python3
"""Side-by-side aligned listing (difflib on regs-unmasked normalized text) of original vs candidate in an original-offset range."""
import sys, os, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llc79, mark79
lab, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
only = len(sys.argv) > 4 and sys.argv[4] == 'diff'
c = mark79.code_of(lab)
ta = llc79.texts(llc79.ORIG); tb = llc79.texts(c)
a = [llc79.norm(t, False) for _, _, t in ta]; b = [llc79.norm(t, False) for _, _, t in tb]
sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    n = max(i2 - i1, j2 - j1)
    for k in range(n):
        ia, ib = i1 + k, j1 + k
        pa = ta[ia][0] if ia < i2 else None
        if pa is None and ia - 1 >= 0 and ia - 1 < len(ta):
            pa_ref = ta[min(ia, len(ta) - 1)][0]
        else:
            pa_ref = pa
        if pa_ref is None or not (lo <= pa_ref < hi):
            continue
        if only and tag == 'equal':
            continue
        sa = f'{ta[ia][0]:6d} {ta[ia][2]}' if ia < i2 else ''
        sb = f'{tb[ib][0]:6d} {tb[ib][2]}' if ib < j2 else ''
        print(f'{"*" if tag != "equal" else " "} {sa:42s} | {sb}')
