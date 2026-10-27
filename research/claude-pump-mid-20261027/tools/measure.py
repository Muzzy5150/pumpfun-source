"""Measure normalized/raw window matches of a candidate against the original.

Original windows come from the frontier inventory; candidate function bodies
come from the candidate's own symbol table. Same normalizer as
scripts/pump_compare_function_bytes.py (direct-call immediates and in-image lddw
values masked).
"""
import sys, json, hashlib, argparse, collections, gzip
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pm
ap = argparse.ArgumentParser()
ap.add_argument('candidate')
ap.add_argument('--base', default=str(pm.WT / 'repro/pump/main-contract-round26-20261027/inventory.json.gz'))
ap.add_argument('--out')
ap.add_argument('--lo', type=lambda s: int(s, 0), default=0x65eb0)
ap.add_argument('--hi', type=lambda s: int(s, 0), default=0xfdf20)
a = ap.parse_args()
inv = pm.read_json(a.base)
ob = pm.ORIG.read_bytes(); cb = Path(a.candidate).read_bytes()
osec, csec = pm.sections(ob), pm.sections(cb)
funcs = pm.candidate_functions(a.candidate)
byn = collections.defaultdict(list)
for s, n, name in funcs:
    raw = pm.body(cb, csec, s, n)
    norm, _ = pm.normalize(raw, s, csec)
    byn[(n, norm)].append((s, name, raw))
res = []; nm = rm = tb = 0
for w in inv['windows']:
    s, n = w['start'], w['bytes']
    raw = pm.body(ob, osec, s, n); norm, _ = pm.normalize(raw, s, osec)
    hits = byn.get((n, norm), [])
    raw_hit = any(r == raw for _, _, r in hits)
    res.append({'start': s, 'bytes': n, 'normalized': bool(hits), 'raw': raw_hit, 'cands': [(c, nmn[-80:]) for c, nmn, _ in hits][:3]})
    nm += bool(hits); rm += raw_hit; tb += n if hits else 0
base = {w['start']: (bool(w['normalized_matches']), w['raw_match']) for w in inv['windows']}
gained = [r for r in res if r['normalized'] and not base[r['start']][0]]
lost = [r for r in res if not r['normalized'] and base[r['start']][0]]
graw = [r for r in res if r['raw'] and not base[r['start']][1]]
lraw = [r for r in res if not r['raw'] and base[r['start']][1]]
summary = {'candidate_sha256': hashlib.sha256(cb).hexdigest(), 'normalized': nm, 'raw': rm, 'matched_text_bytes': tb,
           'gained': [hex(r['start']) for r in gained], 'lost': [hex(r['start']) for r in lost],
           'raw_gained': [hex(r['start']) for r in graw], 'raw_lost': [hex(r['start']) for r in lraw],
           'range_unmatched': sum(1 for r in res if a.lo <= r['start'] <= a.hi and not r['normalized'])}
print(json.dumps(summary))
if a.out:
    Path(a.out).write_text(json.dumps({'summary': summary, 'windows': res}, indent=0))
