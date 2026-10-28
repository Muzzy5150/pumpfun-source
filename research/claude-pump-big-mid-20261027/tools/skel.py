#!/usr/bin/env python3
"""Call skeleton of an original window vs a candidate function.

  skel.py <orig_start> [--cand unstripped.so] [--sym REGEX | --addr 0x..]

Lists, in address order, every call (resolved: original targets are named through the candidate's
matched window symbols from score.py; candidate targets through its symbol table), every Source
site (file:line) and every exit, for both sides, side by side via difflib on the call tokens.
"""
import argparse, difflib, re, struct, sys
from pathlib import Path
CPW = Path('/Users/shawwalters/Documents/Codex/2026-10-24/claude-pump-work')
sys.path.insert(0, str(CPW / 'harness'))
from score import sections, body, original_windows, score, candidate_functions  # noqa
from win import demangle, ORIG, ORIG_SECS  # noqa
from coords import sites  # noqa


def short(name):
    d = demangle(name)
    d = re.sub(r'pump_recovered::', '', d)
    return d[:110]


def skeleton(blob, secs, start, raw, namer):
    out = []
    st = {s['slot']: f"SRC {s['path'].split('/src/')[-1]}:{s['line']}" for s in sites(blob, secs, start, raw)}
    i = 0
    while i < len(raw):
        op = raw[i]
        if i in st:
            out.append((start + i, st[i]))
        if op == 0x85:
            _, regs, off, imm = struct.unpack_from('<BBhi', raw, i)
            if regs >> 4 == 1:
                tgt = start + i + 8 + imm * 8
                out.append((start + i, 'call ' + namer(tgt)))
            else:
                out.append((start + i, f'syscall {imm & 0xffffffff:#x}'))
        elif op == 0x95:
            out.append((start + i, 'exit'))
        i += 16 if op == 0x18 else 8
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('start'); ap.add_argument('--cand', default=str(CPW / 'base/g04/unstripped.so'))
    ap.add_argument('--sym'); ap.add_argument('--addr')
    a = ap.parse_args()
    st = int(a.start, 0)
    w = next(x for x in original_windows() if x['start'] == st)
    cand = Path(a.cand); cb = cand.read_bytes(); cs = sections(cb)
    funcs = candidate_functions(cand)
    byaddr = {s: (n, nm) for s, n, nm in funcs}
    cur = score(cand)
    owin = {x['start']: x for x in original_windows()}
    def oname(t):
        r = cur.get(t)
        if r and r['symbols']:
            return short(r['symbols'][0])
        if t in owin:
            return f'<orig {t:#x} unmatched {owin[t]["bytes"]}B>'
        return f'<orig {t:#x}>'
    def cname(t):
        if t in byaddr:
            return short(byaddr[t][1])
        return f'<cand {t:#x}>'
    if a.addr:
        cs_, = [(s, n, nm) for s, n, nm in funcs if s == int(a.addr, 0)]
    else:
        pat = a.sym
        cands = [(s, n, nm) for s, n, nm in funcs if pat and (re.search(pat, nm) or re.search(pat, demangle(nm)))]
        if not cands:
            sys.exit('no candidate')
        cs_ = cands[0]
    s, n, nm = cs_
    print(f'original {st:#x} {w["bytes"]}B  vs  cand {s:#x} {n}B {short(nm)}')
    O = skeleton(ORIG, ORIG_SECS, st, w['raw'], oname)
    C = skeleton(cb, cs, s, body(cb, cs, s, n), cname)
    sm = difflib.SequenceMatcher(None, [x[1] for x in O], [x[1] for x in C], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                print(f'  {O[i1 + k][0]:#07x} {C[j1 + k][0]:#07x}  {O[i1 + k][1]}')
        else:
            for k in range(i1, i2):
                print(f'- {O[k][0]:#07x}          {O[k][1]}')
            for k in range(j1, j2):
                print(f'+         {C[k][0]:#07x}  {C[k][1]}')


if __name__ == '__main__':
    main()
