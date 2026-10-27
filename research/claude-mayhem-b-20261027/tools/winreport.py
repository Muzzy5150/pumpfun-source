#!/usr/bin/env python3
"""Per-window report for lane windows: candidate counterpart (by symbol pattern), size, normalized equality, diff ratio."""
import sys, difflib
sys.path.insert(0, __import__('os').path.dirname(__file__))
import sbfdis
L='/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/mayhem-b'
O=sbfdis.elf(L+'/wt/evidence/original/mayhem/deployed.so')
W=[('O0073',65472,66384,'FeeRecipient14validate_sweep'),('O0075',69192,77200,'mayhem_recovered16sweep_fees_admin17'),
   ('O0076',77200,85600,'mayhem_recovered10sweep_fees17'),('O0079',95848,113160,'sell_pump_swap7handler'),
   ('O0082',127520,140512,'legacy_sell_handler'),('O0084',159160,177256,'sell_v2_handler'),
   ('O0093',186552,187672,'state10sell_quote')]
def report(path, only=None):
    C=sbfdis.elf(path); cf=sbfdis.funcs(C)
    for wid,s,e,pat in W:
        if only and wid not in only: continue
        cands=[(a,b,n) for a,(b,n) in cf.items() if pat in n]
        if not cands: print(f'{wid}: no candidate for {pat}'); continue
        a,b,n=cands[0]
        ow=O.window(s,e); cw=C.window(a,b)
        eq = (e-s==b-a) and ow['normalized_sha256']==cw['normalized_sha256']
        raw = ow['raw_sha256']==cw['raw_sha256']
        x=[i['norm'] for i in sbfdis.window_insns(O,s,e)]; y=[i['norm'] for i in sbfdis.window_insns(C,a,b)]
        sm=difflib.SequenceMatcher(a=x,b=y,autojunk=False)
        nd=sum(max(i2-i1,j2-j1) for t,i1,i2,j1,j2 in sm.get_opcodes() if t!='equal')
        print(f'{wid}: orig {e-s:6d}  cand {b-a:6d}  norm_eq={eq} raw_eq={raw}  ratio={sm.ratio():.4f} diffslots~{nd}  ({len(cands)} cand)')
if __name__=='__main__':
    report(sys.argv[1], sys.argv[2:] or None)
