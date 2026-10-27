#!/usr/bin/env python3
"""Measure a lane candidate against deployed Mayhem and the provider-sharing baseline.

Uses the frontier packet's reader.py normalizer unchanged and replicates
progress.py's comparison (all 441 original windows; normalized/raw matches,
positive direct edges, Source records and observed Source profiles) without
asserting, so losses are reported instead of raised.

usage: measure.py CANDIDATE_SYMBOLS.so [BASELINE_SYMBOLS.so] [--json OUT]
"""
from pathlib import Path
from collections import defaultdict, Counter
import gzip, hashlib, importlib.util, json, struct, sys

L = Path(__file__).resolve().parent.parent
PKT = L / 'wt/research/mayhem-provider-sharing'
ORIG = L / 'wt/evidence/original/mayhem/deployed.so'
spec = importlib.util.spec_from_file_location('progress_elf', PKT / 'reader.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
MINE = {'O0084', 'O0082', 'O0079', 'O0093', 'O0075', 'O0076', 'O0073'}


def key(w):
    return (w['end'] - w['start'], w['normalized_sha256'], json.dumps(w['normalization_pattern'], sort_keys=True))


def windows(e):
    return {a: e.window(a, z) for a, z in {(s['value'], s['value'] + s['size']) for s in e.symbols
                                            if s['info'] & 15 == 2 and s['size'] >= 8 and e.lo <= s['value'] < e.hi}}


def source(e, p):
    if p not in e.rel or e.rel[p]['type'] != 8:
        return None
    try:
        zero, payload = struct.unpack_from('<II', e.b, p); n, line, col = struct.unpack_from('<QII', e.b, p + 8)
        if zero or not (1 <= n < 300 and 1 <= line < 100000 and 1 <= col < 10000):
            return None
        text = e.b[payload:payload + n].decode()
        return dict(path=text, line=line, column=col) if text.endswith('.rs\0') else None
    except (UnicodeError, struct.error):
        return None


def profile(e, w):
    return {d['offset']: s for d in w['data_references'] if (s := source(e, d['target'])) is not None}


def compare(cand_path, base_path):
    o, b, c = m.Elf(ORIG.resolve()), m.Elf(Path(base_path).resolve()), m.Elf(Path(cand_path).resolve())
    rows = json.loads(gzip.decompress((PKT / 'inputs/parent-audit.json.gz').read_bytes()))['rows']
    ow = {r['start']: o.window(r['start'], r['end']) for r in rows}
    bw, cw = windows(b), windows(c)
    bm, cm = defaultdict(list), defaultdict(list)
    for w in bw.values(): bm[key(w)].append(w)
    for w in cw.values(): cm[key(w)].append(w)
    res = dict(gains=[], body_losses=[], raw_gains=[], raw_losses=[], profile_losses=[], edge_losses=[], source_losses=[],
               source_gains=[], edge_gains=[])
    cnt = Counter()
    status = {}
    for row in rows:
        w = ow[row['start']]; old, new = bm[key(w)], cm[key(w)]
        cnt['matched_before'] += bool(old); cnt['matched_after'] += bool(new)
        rb = any(z['raw_sha256'] == w['raw_sha256'] for z in old); ra = any(z['raw_sha256'] == w['raw_sha256'] for z in new)
        cnt['raw_before'] += rb; cnt['raw_after'] += ra
        status[row['id']] = 'raw_local_match' if ra else 'normalized_only' if new else 'unmatched'
        if rb and not ra: res['raw_losses'].append(row['id'])
        if ra and not rb: res['raw_gains'].append(row['id'])
        if not old and new: res['gains'].append(row['id'])
        if old and not new: res['body_losses'].append(row['id'])
        before_profiles = [profile(b, z) for z in old]; after_profiles = [profile(c, z) for z in new]
        for p in before_profiles:
            if p not in after_profiles: res['profile_losses'].append(dict(id=row['id'], profile=p))
        for d in w['direct']:
            if d['target'] not in ow: continue
            expected = key(ow[d['target']])
            def support(counterparts, index):
                return any(any(x['offset'] == d['offset'] and x['target'] in index and key(index[x['target']]) == expected
                               for x in z['direct']) for z in counterparts)
            yb, yc = support(old, bw), support(new, cw)
            cnt['edges_before'] += yb; cnt['edges_after'] += yc
            if yb and not yc: res['edge_losses'].append(dict(id=row['id'], offset=d['offset']))
            if yc and not yb: res['edge_gains'].append(dict(id=row['id'], offset=d['offset']))
        for ref in w['data_references']:
            expected = source(o, ref['target'])
            if expected is None: continue
            ov = [p.get(ref['offset']) for p in before_profiles]; nv = [p.get(ref['offset']) for p in after_profiles]
            yb, yc = expected in ov, expected in nv
            cnt['source_before'] += yb; cnt['source_after'] += yc
            if yb and not yc: res['source_losses'].append(dict(id=row['id'], offset=ref['offset'], expected=expected))
            if yc and not yb: res['source_gains'].append(dict(id=row['id'], offset=ref['offset'], expected=expected))
    sc = Counter(status.values())
    unmatched = [r for r in rows if status[r['id']] == 'unmatched']
    summary = dict(candidate_symbols_sha256=hashlib.sha256(c.b).hexdigest(), statuses=dict(sc),
                   unmatched_window_bytes=sum(r['end'] - r['start'] for r in unmatched),
                   unmatched_ids=[r['id'] for r in unmatched], counts=dict(cnt),
                   candidate_text_bytes=c.hi - c.lo, candidate_functions=len(cw))
    summary.update({k: v for k, v in res.items()})
    summary['no_losses'] = not any(res[k] for k in ['body_losses', 'raw_losses', 'edge_losses', 'source_losses', 'profile_losses'])
    return summary


if __name__ == '__main__':
    args = sys.argv[1:]
    out = None
    if '--json' in args:
        i = args.index('--json'); out = args[i + 1]; del args[i:i + 2]
    cand = args[0]
    base = args[1] if len(args) > 1 else str(L / 'out/q432/symbols.so')
    s = compare(cand, base)
    short = {k: v for k, v in s.items() if k not in ('profile_losses',)}
    print(json.dumps(short, indent=1, default=str)[:6000])
    if out:
        Path(out).write_text(json.dumps(s, indent=1, default=str) + '\n')
