#!/usr/bin/env python3
"""Heuristic: sequence of AccountInfo copy sources (accounts-struct field offsets) in a window."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import sbfdis, winreport
L = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/mayhem-b'
def seq(insns, lo, hi):
    out = []; P = re.compile(r'ldxdw (r\d), \[(r\d)\+(\d+)\]')
    for k, i in enumerate(insns):
        if not (lo <= i['rel'] < hi): continue
        m = P.match(i['text'])
        if not m: continue
        dst, base, off = m.group(1), m.group(2), int(m.group(3))
        # look ahead: [dst+0] (box deref) then [x+8] / [x+16] (Rc ptr) -> copy source
        nxt = [j['text'] for j in insns[k+1:k+4]]
        if any(re.match(rf'ldxdw r\d, \[{dst}\+(8|16)\]', t) for t in nxt) and off >= 40:
            out.append((i['rel'], off, 'direct'))
        elif any(re.match(rf'ldxdw (r\d), \[{dst}\+0\]', t) for t in nxt) and off >= 40:
            out.append((i['rel'], off, 'box'))
    return out
w = [x for x in winreport.W if x[0] == 'O0079'][0]; O = winreport.O
oi = sbfdis.window_insns(O, w[1], w[2])
for i in oi: i['rel'] = i['pc'] - w[1]
C = sbfdis.elf(f'{L}/out/builds/{sys.argv[1]}/symbols.so'); cf = sbfdis.funcs(C)
a = [a for a, (b, n) in cf.items() if w[3] in n][0]
ci = sbfdis.window_insns(C, a, cf[a][0])
for i in ci: i['rel'] = i['pc'] - a
lo, hi = int(sys.argv[2]), int(sys.argv[3])
so = seq(oi, lo, hi); sc = seq(ci, lo, hi + 1500)
print('orig', [o for _, o, _ in so]); print('cand', [o for _, o, _ in sc])
