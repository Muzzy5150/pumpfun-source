#!/usr/bin/env python3
"""Summarize the diff between an original window and a candidate function: hunks with sizes."""
import difflib, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import sbfdis, winreport
def norm(t, mask_regs):
    t = re.sub(r'call 0x[0-9a-f]+', 'call ?', t)
    t = re.sub(r'(j\w+ .*?)(0x[0-9a-f]+)$', r'\1@', t)
    t = re.sub(r'lddw (r\d+), 0x[0-9a-f]+', r'lddw \1, ?', t) if 'lddw' in t and int(t.split(',')[1], 16) < 0x400000000 else t
    if mask_regs: t = re.sub(r'\br\d\b', 'R', t)
    t = re.sub(r'\[r10-\d+\]', '[fp]', t)
    return t
label, wid = sys.argv[1], sys.argv[2]
mask = len(sys.argv) > 3 and sys.argv[3] == 'regs'
L = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/mayhem-b'
w = [x for x in winreport.W if x[0] == wid][0]; O = winreport.O
C = sbfdis.elf(f'{L}/out/builds/{label}/symbols.so'); cf = sbfdis.funcs(C)
a = [a for a, (b, n) in cf.items() if w[3] in n][0]
oi = sbfdis.window_insns(O, w[1], w[2]); ci = sbfdis.window_insns(C, a, cf[a][0])
A = [norm(i['text'], mask) for i in oi]; B = [norm(i['text'], mask) for i in ci]
sm = difflib.SequenceMatcher(a=A, b=B, autojunk=False)
print(f'{wid} {label}: orig {len(A)} cand {len(B)} ratio(masked fp{"+regs" if mask else ""})={sm.ratio():.4f}')
eq = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal': eq += i2 - i1; continue
    if max(i2 - i1, j2 - j1) >= int(os.environ.get('HMIN', '6')):
        print(f'  {tag:7s} orig[{oi[i1]["pc"]-w[1] if i1 < len(oi) else -1}..+{(i2-i1)*8}] cand[{ci[j1]["pc"]-a if j1 < len(ci) else -1}..+{(j2-j1)*8}]  o:{A[i1] if i1<i2 else ""!s:.40}  c:{B[j1] if j1<j2 else ""!s:.40}')
print('equal insns', eq)
