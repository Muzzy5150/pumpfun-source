#!/usr/bin/env python3
"""IR experiments on the O0079 handler: edit the function body in a rustc .ll, run llc
(same v1.54 platform-tools; reproduces rustc bytes), compare the section with the
original window.

usage: llc79.py BASE.ll EXPS.py [only-label ...]
EXPS.py defines EXPS = [(label, fn(body:str)->str), ...]; fn may return None to skip.
Prints: size, masked(regs+fp) SequenceMatcher ratio vs original, positional diff slots,
and marker positions (constant-2 conversion, variable conversion, udivti3 calls).
Env: LLC_EXTRA="-flag ..." passes extra llc options.
"""
import difflib, importlib.util, os, re, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objsec, sbfdis, winreport
L = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/mayhem-o79'
LLC = '/Users/shawwalters/.cache/solana/v1.54/platform-tools/llvm/bin/llc'
PAT = os.environ.get('L79_PAT', 'sell_pump_swap7handler')
W = [x for x in winreport.W if x[0] == 'O0079'][0]
O = winreport.O
ORIG = O.b[W[1]:W[2]]


def texts(code):
    out = []
    for pc, raw in objsec.insns(code):
        t = sbfdis.decode(code, None, pc, pc + len(raw), None, None)[0]['text']
        out.append((pc, raw, t))
    return out


def norm(t, regs=True):
    t = re.sub(r'^(call|syscall) .*', 'call ?', t)
    if t.startswith('lddw'):
        t = re.sub(r'lddw (r\d+), 0x[0-9a-f]+', r'lddw \1, ?', t)
    t = re.sub(r'(j\w+ .*?)(0x[0-9a-f]+)$', r'\1@', t)
    t = re.sub(r'^ja @.*', 'ja @', t)
    t = re.sub(r'\[r10-\d+\]', '[fp]', t)
    t = re.sub(r'^(add64 r\d+), -(\d{3,})$', r'\1, -K', t)
    if regs:
        t = re.sub(r'\br\d\b', 'R', t)
    return t


def ratio(code, regs=True):
    a = [norm(t, regs) for _, _, t in texts(ORIG)]
    b = [norm(t, regs) for _, _, t in texts(code)]
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def markers(code):
    out = []
    tt = texts(code)
    for k, (pc, raw, t) in enumerate(tt):
        if re.match(r'stw \[r10-\d+\], 2$', t):
            out.append(f'c2@{pc}')
        if re.match(r'or64 r\d, 6000$', t):
            out.append(f'cv@{pc}')
        if t.startswith('exit'):
            out.append(f'exit@{pc}')
    return out


def span(s):
    m = re.search(r'\ndefine[^\n]*' + PAT + r'[^\n]*\n', s)
    st = m.start() + 1
    return st, s.find('\n}\n', st) + 2


def compile_ll(text, label):
    out = f'{L}/out/llc/{label}.ll'
    open(out, 'w').write(text)
    cmd = [LLC, '-O3', '-mtriple=sbf', '-mcpu=generic', '-relocation-model=pic', '-function-sections',
           '-filetype=obj', out, '-o', f'{L}/out/llc/{label}.o'] + os.environ.get('LLC_EXTRA', '').split()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        return None, r.stderr[:1500]
    secs = objsec.sections(f'{L}/out/llc/{label}.o')
    key = [k for k in secs if PAT in k and k.startswith('.text')][0]
    open(f'{L}/out/llc/{label}.bin', 'wb').write(secs[key])
    return secs[key], r.stderr


def prefix(code):
    a = [norm(t, False) for _, _, t in texts(ORIG)]
    b = [norm(t, False) for _, _, t in texts(code)]
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def regdiff(code, lo=0, hi=None):
    """number of non-equal aligned slots (regs NOT masked, fp masked) in [lo,hi) of the original"""
    ta = texts(ORIG); tb = texts(code)
    a = [norm(t, False) for _, _, t in ta]; b = [norm(t, False) for _, _, t in tb]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    nd = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        o1 = ta[i1][0] if i1 < len(ta) else len(ORIG)
        if hi is not None and o1 >= hi:
            continue
        if o1 < lo:
            continue
        nd += max(i2 - i1, j2 - j1)
    return nd


def report(label, code):
    r = ratio(code)
    pf = prefix(code); rd = regdiff(code, 0, 2800)
    o = objsec.norm(ORIG); c = objsec.norm(code)
    neq = sum(1 for a, b in zip(o, c) if a != b) + abs(len(o) - len(c))
    print(f'{label}: size {len(code)} ratio {r:.4f} prefix {pf} rd2800 {rd} posdiff {neq} | {" ".join(markers(code))}', flush=True)


if __name__ == '__main__':
    base = open(sys.argv[1]).read()
    st, en = span(base)
    body = base[st:en]
    spec = importlib.util.spec_from_file_location('exps', sys.argv[2]); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    only = set(sys.argv[3:])
    for label, fn in m.EXPS:
        if only and label not in only:
            continue
        try:
            nb = fn(body)
        except Exception as e:  # noqa: BLE001
            print(f'{label}: EDIT FAILED {e!r}', flush=True); continue
        if nb is None:
            continue
        code, err = compile_ll(base[:st] + nb + base[en:], label)
        if code is None:
            print(f'{label}: LLC FAILED {err}', flush=True); continue
        report(label, code)
