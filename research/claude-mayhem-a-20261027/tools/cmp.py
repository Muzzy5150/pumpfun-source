#!/usr/bin/env python3
"""Compare an original window against a candidate function with normalized operands.

usage: cmp.py ORIG_START CAND_START_OR_NAME [--cand PATH] [--full] [--calls]
"""
import sys, struct, difflib, argparse, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sbf

LANE = sbf.LANE
ap = argparse.ArgumentParser()
ap.add_argument('orig', type=int)
ap.add_argument('cand')
ap.add_argument('--cand-elf', default=str(LANE / 'out/art/v3-symbols.so'))
ap.add_argument('--orig-elf', default=str(LANE / 'out/art/original.so'))
ap.add_argument('--full', action='store_true', help='print full side-by-side')
ap.add_argument('--calls', action='store_true', help='print call sequences only')
ap.add_argument('--ctx', type=int, default=3)
ap.add_argument('--listing', action='store_true')
a = ap.parse_args()

O = sbf.E(a.orig_elf)
C = sbf.E(a.cand_elf)
rows = sbf.orig_rows()
by_start = {r['start']: r for r in rows}
# candidate address -> original ids that list it as counterpart (in frontier symbols build)
cand2orig = collections.defaultdict(list)
name2orig = collections.defaultdict(set)
for r in rows:
    for p in r['counterparts']:
        cand2orig[p['start']].append(r['id'])
        for n in p['names']:
            name2orig[n].add(r['id'])


def data_label(elf, va):
    # describe data target
    for s in elf.sections:
        if s['address'] <= va < s['address'] + s['size'] and s['type'] != 8:
            off = va - s['address']
            b = elf.b[s['offset'] + off: s['offset'] + off + 64]
            if s['name'] == '.data.rel.ro':
                # Location? ptr,len,line,col
                ptr, ln = struct.unpack_from('<QQ', b, 0)
                if ptr and ptr & 0xffffffff == 0:
                    ptr >>= 32
                line, col = struct.unpack_from('<II', b, 16)
                for t in elf.sections:
                    if t['name'] == '.rodata' and t['address'] <= ptr < t['address'] + t['size'] and 0 < ln < 200:
                        st = elf.b[t['offset'] + ptr - t['address']: t['offset'] + ptr - t['address'] + ln]
                        try:
                            txt = st.rstrip(b'\0').decode()
                        except Exception:
                            txt = None
                        if txt and txt.isprintable():
                            if txt.endswith('.rs') and line < 100000 and col < 1000:
                                return f' ;Loc({txt}:{line}:{col})'
                            return f' ;&str{txt[:40]!r}'
                return f' ;rel.ro+{off:#x}'
            if s['name'] == '.rodata':
                txt = b.split(b'\0')[0][:40]
                try:
                    t = txt.decode()
                    if len(t) >= 4 and t.isprintable():
                        return f' ;"{t}"'
                except Exception:
                    pass
                return f' ;ro+{off:#x}'
            return f' ;{s["name"]}+{off:#x}'
    return f' ;?{va:#x}'


def onamer(kind, v):
    if kind == 'data':
        return data_label(O, v)
    r = by_start.get(v)
    if r is None:
        return f'O?{v:#x}'
    names = [n for p in r['counterparts'] for n in p['names']]
    nm = sbf.demangle(names[0])[-60:] if names else '?'
    return f'{r["id"]}<{nm}>'


def cnamer(kind, v):
    if kind == 'data':
        return data_label(C, v)
    nms = [n for n, _ in C.funcs.get(v, [('?', 0)])]
    ids = sorted(set().union(*[name2orig.get(n, set()) for n in nms]))
    nm = nms[0]
    nm = sbf.demangle(nm)[-60:]
    if len(ids) == 1:
        return f'{ids[0]}<{nm}>'
    if ids:
        return f'{"/".join(ids)}<{nm}>'
    return f'C?{v:#x}<{nm}>'


r = by_start[a.orig]
ostart, oend = r['start'], r['end']
if a.cand.isdigit():
    cs = int(a.cand)
else:
    hits = [(v, n, s) for v, ns in C.funcs.items() for n, s in ns if a.cand in n or a.cand in sbf.demangle(n)]
    if len(hits) != 1:
        for h in hits[:20]:
            print(h[0], h[2], sbf.demangle(h[1]))
        sys.exit(f'{len(hits)} candidate hits')
    cs = hits[0][0]
csize = C.funcs[cs][0][1]
cend = cs + csize
print(f'original {r["id"]} {ostart}..{oend} ({oend-ostart} B)  candidate {cs}..{cend} ({csize} B) {sbf.demangle(C.funcs[cs][0][0])}')
od = sbf.decode(O, ostart, oend, onamer)
cd = sbf.decode(C, cs, cend, cnamer)
ot = [t for _, t, _ in od]
ct = [t for _, t, _ in cd]
if a.listing:
    print('--- original')
    for i, t in enumerate(ot):
        print(f'{i:5d}  {t}')
    print('--- candidate')
    for i, t in enumerate(ct):
        print(f'{i:5d}  {t}')
    sys.exit()
if a.calls:
    oc =[t for _, t, k in od if k in ('call', 'syscall', 'callx') or t.startswith('syscall')]
    cc = [t for _, t, k in cd if k in ('call', 'syscall', 'callx') or t.startswith('syscall')]
    sm = difflib.SequenceMatcher(None, oc, cc, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                print(f'   = {oc[i1+k]}')
        else:
            for k in range(i1, i2):
                print(f'  -O {oc[k]}')
            for k in range(j1, j2):
                print(f'  +C {cc[k]}')
    sys.exit()
sm = difflib.SequenceMatcher(None, ot, ct, autojunk=False)
print(f'ratio {sm.ratio():.4f}; orig insns {len(ot)} cand insns {len(ct)}')
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        if a.full:
            for k in range(i2 - i1):
                print(f'  {i1+k:5d} {j1+k:5d}   {ot[i1+k]}')
        else:
            n = i2 - i1
            if n <= 2 * a.ctx:
                for k in range(n):
                    print(f'  {i1+k:5d} {j1+k:5d}   {ot[i1+k]}')
            else:
                for k in range(a.ctx):
                    print(f'  {i1+k:5d} {j1+k:5d}   {ot[i1+k]}')
                print(f'  ... {n - 2*a.ctx} equal ...')
                for k in range(n - a.ctx, n):
                    print(f'  {i1+k:5d} {j1+k:5d}   {ot[i1+k]}')
    else:
        for k in range(i1, i2):
            print(f'- {k:5d}       O {ot[k]}')
        for k in range(j1, j2):
            print(f'+       {k:5d} C {ct[k]}')
