#!/usr/bin/env python3
"""Call graph helpers over original windows / candidate functions."""
import sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sbf
LANE = sbf.LANE

def windows_orig(O, rows):
    return [(r['start'], r['end'], r['id']) for r in rows]

def calls_in(elf, s, e):
    out = []
    for pc, t, k in sbf.decode(elf, s, e, None):
        if k == 'call' and t.startswith('call 0x'):
            out.append((pc, int(t.split()[1], 16)))
    return out

if __name__ == '__main__':
    O = sbf.E(str(LANE / 'out/art/original.so'))
    rows = sbf.orig_rows()
    byid = {r['id']: r for r in rows}
    bystart = {r['start']: r for r in rows}
    callers = collections.defaultdict(list)
    for r in rows:
        for pc, t in calls_in(O, r['start'], r['end']):
            callers[t].append((r['id'], pc - r['start']))
    for wid in sys.argv[1:]:
        r = byid[wid]
        names = [sbf.demangle(n) for p in r['counterparts'] for n in p['names']][:3]
        print(f"{wid} {r['start']}..{r['end']} {r['bytes']}B status={r['status']} names={names}")
        print('  callers:', callers.get(r['start']))
        cs = calls_in(O, r['start'], r['end'])
        print('  callees:', [(off - r['start'], bystart[t]['id'] if t in bystart else hex(t)) for off, t in cs])
