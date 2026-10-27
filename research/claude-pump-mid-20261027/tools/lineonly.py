"""Find unmatched original windows whose nearest equal-length candidate differs only in
immediate operands of store-immediate instructions (stw/stdw/sth/stb)."""
import sys, json, struct, collections, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pm
ap = argparse.ArgumentParser(); ap.add_argument('--candidate', default=str(pm.WT/'repro/pump/main-contract-round26-20261027/unstripped.so'))
ap.add_argument('--lo', type=lambda s:int(s,0), default=0); ap.add_argument('--hi', type=lambda s:int(s,0), default=1<<40)
ap.add_argument('--maxdiff', type=int, default=8)
a = ap.parse_args()
inv = pm.read_json(pm.WT/'repro/pump/main-contract-round26-20261027/inventory.json.gz')
ob = pm.ORIG.read_bytes(); cb = Path(a.candidate).read_bytes(); osec, csec = pm.sections(ob), pm.sections(cb)
funcs = pm.candidate_functions(a.candidate)
c2o = {m['start'] for w in inv['windows'] for m in w['normalized_matches']}
byn = collections.defaultdict(list)
for s, n, name in funcs:
    byn[n].append((s, name, pm.normalize(pm.body(cb, csec, s, n), s, csec)[0]))
out = []
for w in inv['windows']:
    if w['normalized_matches'] or not (a.lo <= w['start'] <= a.hi): continue
    s, n = w['start'], w['bytes']
    on = pm.normalize(pm.body(ob, osec, s, n), s, osec)[0]
    best = None
    for cs, name, cn in byn[n]:
        diffs = [i for i in range(0, n, 8) if on[i:i+8] != cn[i:i+8]]
        if len(diffs) > a.maxdiff: continue
        imm_only = all(on[i:i+4] == cn[i:i+4] and on[i] in (0x62, 0x7a, 0x6a, 0x72) for i in diffs)
        rec = (len(diffs), imm_only, cs, name, [(i, on[i:i+8].hex(), struct.unpack_from('<i', on, i+4)[0], struct.unpack_from('<i', cn, i+4)[0]) for i in diffs])
        if best is None or (rec[1], -rec[0]) > (best[1], -best[0]): best = rec
    if best:
        out.append({'start': hex(s), 'bytes': n, 'ndiff': best[0], 'imm_only': best[1], 'cand': hex(best[2]), 'cand_in_use': best[2] in c2o, 'name': best[3][-90:], 'diffs': best[4]})
for r in sorted(out, key=lambda r: (not r['imm_only'], r['ndiff'])):
    print(r['start'], r['bytes'], 'ndiff', r['ndiff'], 'imm_only' if r['imm_only'] else 'OTHER', r['cand'], 'USED' if r['cand_in_use'] else '', r['name'][-70:], [(d[0], d[2], d[3]) for d in r['diffs']][:6])
