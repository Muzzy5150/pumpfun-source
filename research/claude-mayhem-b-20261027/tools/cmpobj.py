#!/usr/bin/env python3
"""Compare an llc-produced function section against the original window and a candidate ELF function (masked call/lddw)."""
import sys, struct
sys.path.insert(0, __import__('os').path.dirname(__file__))
import sbfdis, objsec, winreport
def masked_from_elf(E, s, e):
    code=E.b[s:e]; return objsec.norm(code)
def report(binpath, wid, cand_so=None):
    w=[x for x in winreport.W if x[0]==wid][0]
    O=winreport.O
    orig=masked_from_elf(O, w[1], w[2])
    obj=objsec.norm(open(binpath,'rb').read())
    neq=sum(1 for a,b in zip(orig,obj) if a!=b)+abs(len(orig)-len(obj))
    print(f'{wid}: orig {w[2]-w[1]} obj {sum(len(x) for x in obj)} differing-slots(masked call/lddw, positional)={neq}')
    if cand_so:
        C=sbfdis.elf(cand_so); cf=sbfdis.funcs(C)
        a=[a for a,(b,n) in cf.items() if w[3] in n][0]
        cand=masked_from_elf(C,a,cf[a][0])
        print('  obj == rustc candidate (masked):', cand==obj)
    first=[i for i,(a,b) in enumerate(zip(orig,obj)) if a!=b][:12]
    print('  first differing insn idx:', first)
if __name__=='__main__':
    report(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else None)
