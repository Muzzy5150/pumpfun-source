#!/usr/bin/env python3
"""Measure a candidate symbols ELF against the 441 original Mayhem windows.

Replicates the packet analysis rule (research/mayhem-*/analysis.py): an original
window matches when a candidate FUNC symbol range has the same size, normalized
sha256 and normalization pattern (reader.Elf.window); raw_local when the raw
bytes are also equal.

usage: measure.py SYMBOLS_SO [--base BASE_SYMBOLS_SO] [--ids O0083,...] [--json OUT]
"""
import argparse, collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sbf

ap = argparse.ArgumentParser()
ap.add_argument('symbols')
ap.add_argument('--base')
ap.add_argument('--ids', default='O0083,O0081,O0077,O0092,O0095,O0193,O0209,O0210,O0237,O0238')
ap.add_argument('--json')
a = ap.parse_args()

O = sbf.E(str(sbf.LANE / 'out/art/original.so'))
rows = sbf.orig_rows()


def sig(w):
    return (w['end'] - w['start'], w['normalized_sha256'], json.dumps(w['normalization_pattern'], sort_keys=True))


ow = {r['id']: O.window(r['start'], r['end']) for r in rows}


def measure(path):
    C = sbf.E(path)
    groups = {}
    for f in C.symbols:
        if f['info'] & 15 == 2 and f['size'] >= 8 and C.lo <= f['value'] < C.hi:
            groups.setdefault((f['value'], f['value'] + f['size']), set()).add(f['name'])
    cw = {k: C.window(*k) for k in groups}
    bysig = collections.defaultdict(list)
    for k, w in cw.items():
        bysig[sig(w)].append(k)
    st = {}
    for r in rows:
        w = ow[r['id']]
        m = bysig.get(sig(w), [])
        raw = any(cw[k]['raw_sha256'] == w['raw_sha256'] for k in m)
        st[r['id']] = ('raw_local_match' if raw else 'normalized_only' if m else 'unmatched', [k[0] for k in m])
    return st, C


st, C = measure(a.symbols)
cnt = collections.Counter(v[0] for v in st.values())
matched = cnt['raw_local_match'] + cnt['normalized_only']
unm = [i for i, v in st.items() if v[0] == 'unmatched']
unm_bytes = sum(r['bytes'] for r in rows if r['id'] in unm)
print(f'{a.symbols}: normalized={matched} raw_local={cnt["raw_local_match"]} unmatched={len(unm)} ({unm_bytes} B) text={C.hi - C.lo}')
print('unmatched:', ' '.join(unm))
for i in a.ids.split(','):
    if i in st:
        print(f'  {i}: {st[i][0]} {st[i][1][:4]}')
out = dict(symbols=a.symbols, normalized=matched, raw_local=cnt['raw_local_match'], unmatched=unm, unmatched_bytes=unm_bytes,
           status={k: v[0] for k, v in st.items()})
if a.base:
    bst, _ = measure(a.base)
    gains = [i for i in st if bst[i][0] == 'unmatched' and st[i][0] != 'unmatched']
    losses = [i for i in st if bst[i][0] != 'unmatched' and st[i][0] == 'unmatched']
    rg = [i for i in st if bst[i][0] != 'raw_local_match' and st[i][0] == 'raw_local_match']
    rl = [i for i in st if bst[i][0] == 'raw_local_match' and st[i][0] != 'raw_local_match']
    bc = collections.Counter(v[0] for v in bst.values())
    print(f'base {a.base}: normalized={bc["raw_local_match"] + bc["normalized_only"]} raw_local={bc["raw_local_match"]}')
    print(f'normalized gains={gains} losses={losses}')
    print(f'raw gains={rg}')
    print(f'raw losses={rl}')
    out.update(base=a.base, gains=gains, losses=losses, raw_gains=rg, raw_losses=rl)
if a.json:
    Path(a.json).write_text(json.dumps(out, indent=1) + '\n')
