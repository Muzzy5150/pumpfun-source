#!/usr/bin/env python3
"""Diff an llc-produced function (.o section) against an original window, by normalized instruction text."""
import difflib, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import objsec, sbfdis, winreport

def texts(code):
    out = []
    for pc, raw in objsec.insns(code):
        t = sbfdis.decode(code, None, pc, pc + len(raw), None, None)[0]['text']
        t = re.sub(r'call 0x[0-9a-f]+', 'call ?', t)
        if raw[0] == 0x18: t = re.sub(r'lddw (r\d+), 0x[0-9a-f]+', r'lddw \1, ?', t)
        out.append((pc, t))
    return out

def jnorm(seq):
    # make branch targets relative-insensitive: replace absolute targets by '@'
    return [re.sub(r'(0x[0-9a-f]+|@\d+)$', '@', t) if t.split()[0].startswith('j') else t for _, t in seq]

if __name__ == '__main__':
    obj, sec, wid = sys.argv[1], sys.argv[2], sys.argv[3]
    maxl = int(sys.argv[4]) if len(sys.argv) > 4 else 200
    secs = objsec.sections(obj); key = [k for k in secs if sec in k and k.startswith('.text')][0]
    cand = texts(secs[key])
    w = [x for x in winreport.W if x[0] == wid][0]
    O = winreport.O
    orig = texts(O.b[w[1]:w[2]])
    a, b = jnorm(orig), jnorm(cand)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    print(f'orig {len(orig)} insns, cand {len(cand)} insns, ratio {sm.ratio():.4f}')
    n = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            if i2 - i1 > 6:
                print(f'   ... {i2-i1} equal ...'); continue
            for k in range(i1, i2): print(f'  {orig[k][0]:6d} {orig[k][1]}')
            continue
        for k in range(i1, i2): print(f'- {orig[k][0]:6d} {orig[k][1]}')
        for k in range(j1, j2): print(f'+ {cand[k][0]:6d} {cand[k][1]}')
        n += 1
        if n > maxl: break
