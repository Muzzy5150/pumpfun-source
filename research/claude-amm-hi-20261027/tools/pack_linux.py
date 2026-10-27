#!/usr/bin/env python3
"""Pack a Linux-recipe build into the lane packet: gzipped stripped and unstripped ELFs,
their SHA-256 (raw and gzip), the measure.py JSON (gzip), the build record and log, the
window delta against a base measurement, and the runtime suite summary (with receipts).

usage: pack_linux.py <build-tag> <dest-name> --base <base-build-tag> [--runtime <runtime-dir>]
"""
import argparse, gzip, hashlib, json, shutil, sys
from pathlib import Path
LANE = Path('/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/amm-hi')
PK = LANE / 'wt/research/claude-amm-hi-20261027'
def sha(b): return hashlib.sha256(b).hexdigest()
def gz(data): return gzip.compress(data, compresslevel=9, mtime=0)
ap = argparse.ArgumentParser(); ap.add_argument('tag'); ap.add_argument('dest'); ap.add_argument('--base', required=True); ap.add_argument('--runtime')
a = ap.parse_args()
b = LANE / 'out/builds' / a.tag; d = PK / 'linux' / a.dest
if d.exists(): shutil.rmtree(d)
d.mkdir(parents=True)
hashes = {}
for name in ('candidate.so', 'unstripped.so'):
    raw = (b / name).read_bytes(); z = gz(raw)
    (d / (name + '.gz')).write_bytes(z)
    hashes[name] = {'sha256': sha(raw), 'bytes': len(raw), 'gzip_sha256': sha(z)}
m = json.loads((b / 'measurement.json').read_text())
(d / 'measurement.json.gz').write_bytes(gz((b / 'measurement.json').read_bytes()))
rec = json.loads((b / 'build.json').read_text())
rec.pop('workspace_inputs', None)
(d / 'build.json').write_text(json.dumps(rec, indent=1) + '\n')
(d / 'workspace-inputs.json').write_text(json.dumps(json.loads((b / 'build.json').read_text()).get('workspace_inputs', {}), indent=1) + '\n')
(d / 'build.log.gz').write_bytes(gz((b / 'build.log').read_bytes()))
base = json.loads((LANE / 'out/builds' / a.base / 'measurement.json').read_text())
rb = {r['start']: r for r in base['rows']}; rc = {r['start']: r for r in m['rows']}
delta = []
for st in sorted(rc):
    x, y = rb.get(st), rc[st]
    nx, ny = bool(x and x['matches']), bool(y['matches']); qx, qy = bool(x and x['raw_match']), bool(y['raw_match'])
    if nx != ny or qx != qy:
        delta.append({'original_start': hex(st), 'bytes': y['end'] - st, 'normalized': [nx, ny], 'raw': [qx, qy],
                      'candidate_symbol': (y['matches'] or (x or {}).get('matches') or [{'name': None}])[0]['name']})
summary = {'build_tag': a.tag, 'base_build_tag': a.base, 'base_candidate_sha256': base['candidate_sha256'],
           'artifacts': hashes, 'measurement': {k: m[k] for k in ('candidate_sha256', 'symbols_sha256', 'reader_sha256', 'windows', 'normalized_matches', 'raw_matches', 'unmatched')},
           'base_measurement': {k: base[k] for k in ('normalized_matches', 'raw_matches', 'unmatched')},
           'window_delta': delta, 'losses': [x for x in delta if x['normalized'] == [True, False] or x['raw'] == [True, False]],
           'measure_command': 'python3 repro/pump_amm/focused-diagnostics-20261026/measure.py --candidate candidate.so --symbols unstripped.so --output measurement.json'}
assert hashes['candidate.so']['sha256'] == m['candidate_sha256'] and hashes['unstripped.so']['sha256'] == m['symbols_sha256']
if a.runtime:
    rt = Path(a.runtime); s = json.loads((rt / 'summary.json').read_text())
    assert s['candidate_sha256'] == hashes['candidate.so']['sha256'], 'runtime ran on a different candidate'
    (d / 'runtime').mkdir()
    (d / 'runtime/summary.json').write_text(json.dumps(s, indent=1) + '\n')
    for f in sorted(rt.glob('*.json')):
        if f.name != 'summary.json': (d / 'runtime' / (f.name + '.gz')).write_bytes(gz(f.read_bytes()))
    summary['runtime'] = {k: s[k] for k in ('suites', 'cases', 'mismatches', 'all_pass')}
(d / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
print(json.dumps({k: summary[k] for k in ('measurement', 'base_measurement')} | {'gains': len(delta) - len(summary['losses']), 'losses': len(summary['losses']), 'runtime': summary.get('runtime')}))
