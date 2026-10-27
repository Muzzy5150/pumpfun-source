#!/usr/bin/env python3
"""Extract (error code, Source filename, line) from error!-closure bodies."""
import sys, re, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sbfdiff import sections, dis, symtab
def rd(blob, secs, v, n):
    for s in secs.values():
        if s['addr'] > 0 and s['addr'] <= v < s['addr'] + s['size']:
            off = v - s['addr'] + s['offset']; return blob[off:off+n]
def body(blob, secs, a, n):
    t = secs['.text']; return blob[a-t['addr']+t['offset']:a-t['addr']+t['offset']+n]
def sites(blob, secs, a, n):
    """find all stores of filename ptr/len + line in a body"""
    d = dis(body(blob, secs, a, n), a, secs); txt = [x[2] for x in d]
    out = []
    for k, x in enumerate(txt):
        m = re.match(r'lddw r(\d), (0x[0-9a-f]+) <\.rodata>', x)
        if not m: continue
        reg, ptr = m.group(1), int(m.group(2), 16)
        # look ahead for stxdw [r10-X], r<reg> then stdw [r10-(X-8)], LEN and stw [r10-(X-16)], LINE
        for y in txt[k+1:k+12]:
            m2 = re.match(rf'stxdw \[r10-(\d+)\], r{reg}$', y)
            if m2:
                X = int(m2.group(1)); ln = line = None
                for z in txt[max(0,k-12):k+16]:
                    m3 = re.match(rf'stdw \[r10-{X-8}\], (\d+)$', z)
                    if m3: ln = int(m3.group(1))
                    m4 = re.match(rf'stw \[r10-{X-16}\], (\d+)$', z)
                    if m4: line = int(m4.group(1))
                if ln and line is not None and 5 < ln < 120:
                    s = rd(blob, secs, ptr, ln)
                    try: s = s.decode()
                    except Exception: s = None
                    if s and ('.rs' in s): out.append((s, line))
                break
    codes = sorted({int(m.group(1)) for x in txt for m in [re.match(r'stw \[r10-\d+\], (\d+)$', x)] if m and 6000 <= int(m.group(1)) < 6200})
    return out, codes
if __name__ == '__main__':
    O = Path(sys.argv[1]); C = Path(sys.argv[2]); wins = json.load(open(sys.argv[3]))
    ob, cb = O.read_bytes(), C.read_bytes(); os_, cs = sections(ob), sections(cb)
    for r in wins:
        if r['bytes'] > int(sys.argv[4]) : continue
        print(r['hex'], r['bytes'], 'orig', sites(ob, os_, r['start'], r['bytes']))
    syms, funcs = symtab(C)
    print('--- candidate closures (520)')
    for a, n, nm in funcs:
        if n == 520:
            print(hex(a), sites(cb, cs, a, n), re.sub(r'17h[0-9a-f]{16}E$', '', nm)[-50:])
