#!/usr/bin/env python3
"""pm-o84 IR surgery: edit sell_v2_handler in a rustc-emitted .ll, run llc, compare with O0084.

usage: irx.py BASE.ll EXPS.py [label-filter]
EXPS.py defines EXPS=[(label, fn(text)->text)] operating on the function body text.
Prints: label, bytes, positional masked diff slots, stack+reg-masked difflib ratio and #diff lines.
"""
import importlib.util, re, subprocess, sys, difflib
sys.path.insert(0, '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/mayhem-b/build')
import objsec, sbfdis, winreport
OUT = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/o84/out/llc'
LLC = '/Users/shawwalters/.cache/solana/v1.54/platform-tools/llvm/bin/llc'
PAT = 'sell_v2_handler'
O = winreport.O
W = [x for x in winreport.W if x[0] == 'O0084'][0]
ORIG = objsec.norm(O.b[W[1]:W[2]])
import os
os.makedirs(OUT, exist_ok=True)

def span(s):
    m = re.search(r'\ndefine[^\n]*' + PAT + r'[^\n]*\n', s); st = m.start() + 1
    return st, s.find('\n}\n', st) + 2

def masked_lines(code, base):
    out = []
    for pc, raw in objsec.insns(code):
        t = sbfdis.decode(code, None, pc, pc + len(raw), None, None)[0]['text']
        t = re.sub(r'\[r10-\d+\]', '[r10-S]', t); t = re.sub(r'add64 (r\d+), -\d+$', r'add64 \1, -K', t)
        t = re.sub(r'r\d+', 'rX', t)
        t = re.sub(r'call 0x[0-9a-f]+', 'call F', t); t = re.sub(r'lddw rX, 0x[0-9a-f]+', 'lddw rX, P', t)
        t = re.sub(r'(j\w+ .*, )0x[0-9a-f]+$', r'\1J', t); t = re.sub(r'^ja 0x[0-9a-f]+$', 'ja J', t)
        out.append(t)
    return out

ORIG_LINES = masked_lines(O.b[W[1]:W[2]], W[1])

def compile_text(full, label):
    p = f'{OUT}/{label}.ll'; open(p, 'w').write(full)
    r = subprocess.run([LLC, '-O3', '-mtriple=sbf', '-mcpu=generic', '-relocation-model=pic', '-function-sections',
                        '-filetype=obj', p, '-o', f'{OUT}/{label}.o'], capture_output=True, text=True)
    if r.returncode:
        return None, r.stderr[-800:]
    secs = objsec.sections(f'{OUT}/{label}.o')
    key = [k for k in secs if PAT in k and k.startswith('.text')][0]
    return secs[key], None

def score(code):
    obj = objsec.norm(code)
    pos = sum(1 for a, b in zip(ORIG, obj) if a != b) + abs(len(ORIG) - len(obj))
    ml = masked_lines(code, 0)
    sm = difflib.SequenceMatcher(a=ORIG_LINES, b=ml, autojunk=False)
    nd = sum(max(i2 - i1, j2 - j1) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != 'equal')
    return len(code), pos, round(sm.ratio(), 4), nd

if __name__ == '__main__':
    s = open(sys.argv[1]).read(); st, en = span(s); body = s[st:en]
    spec = importlib.util.spec_from_file_location('exps', sys.argv[2]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    filt = sys.argv[3] if len(sys.argv) > 3 else None
    for label, fn in m.EXPS:
        if filt and filt not in label: continue
        try:
            nb = fn(body)
        except Exception as e:
            print(f'{label}: EDIT FAILED {e!r}'); continue
        code, err = compile_text(s[:st] + nb + s[en:], label)
        if code is None:
            print(f'{label}: LLC FAILED {err}'); continue
        print(label, *score(code), flush=True)

def show(label, maxhunks=40, context=2):
    secs = objsec.sections(f'{OUT}/{label}.o')
    key = [k for k in secs if PAT in k and k.startswith('.text')][0]
    code = secs[key]
    a = ORIG_LINES; b = masked_lines(code, 0)
    at = [sbfdis.decode(O.b[W[1]:W[2]], None, pc, pc + len(raw), None, None)[0]['text'] for pc, raw in objsec.insns(O.b[W[1]:W[2]])]
    apc = [pc for pc, raw in objsec.insns(O.b[W[1]:W[2]])]
    bt = [sbfdis.decode(code, None, pc, pc + len(raw), None, None)[0]['text'] for pc, raw in objsec.insns(code)]
    bpc = [pc for pc, raw in objsec.insns(code)]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False); h = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal': continue
        h += 1
        if h > maxhunks: print('...'); break
        print(f'@@ O+{apc[i1] if i1 < len(apc) else "end"} C+{bpc[j1] if j1 < len(bpc) else "end"}')
        for k in range(max(0, i1 - context), i1): print(f'   {apc[k]:6d}  {at[k]}')
        for k in range(i1, i2): print(f'-  {apc[k]:6d}  {at[k]}')
        for k in range(j1, j2): print(f'+         {bpc[k]:6d}  {bt[k]}')

def show_code(code, maxhunks=40, context=2, lo=0, hi=1 << 30):
    a = ORIG_LINES; b = masked_lines(code, 0)
    oc = O.b[W[1]:W[2]]
    at = [sbfdis.decode(oc, None, pc, pc + len(raw), None, None)[0]['text'] for pc, raw in objsec.insns(oc)]
    apc = [pc for pc, raw in objsec.insns(oc)]
    bt = [sbfdis.decode(code, None, pc, pc + len(raw), None, None)[0]['text'] for pc, raw in objsec.insns(code)]
    bpc = [pc for pc, raw in objsec.insns(code)]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False); h = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal': continue
        if i1 < len(apc) and not (lo <= apc[i1] < hi): continue
        h += 1
        if h > maxhunks: print('...'); break
        print(f'@@ O+{apc[i1] if i1 < len(apc) else "end"} C+{bpc[j1] if j1 < len(bpc) else "end"}')
        for k in range(max(0, i1 - context), i1): print(f'   {apc[k]:6d}  {at[k]}')
        for k in range(i1, i2): print(f'-  {apc[k]:6d}  {at[k]}')
        for k in range(j1, j2): print(f'+         {bpc[k]:6d}  {bt[k]}')

def elf_code(path):
    C = sbfdis.elf(path); cf = sbfdis.funcs(C)
    a = [a for a, (b, n) in cf.items() if 'sell_v2_handler' in n][0]
    return C.b[a:cf[a][0]]
