"""Signed CreateV2 missing-chain/pool account boundaries, with no companion CPI."""
from pathlib import Path
import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
H = ROOT / 'work/pump-nested-current21/proposed'
sys.path.insert(0, str(H))
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('tail_fixture', H / 'pump_nested_general_differential.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
p = argparse.ArgumentParser()
p.add_argument('--candidate', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
cases = []
for depth, pools in [(1, [0]), (2, []), (3, []), (2, [0]), (2, [1])]:
    count = depth - 1 + 3 * len(pools)
    for keep in range(count + 1):
        cases.append({'depth': depth, 'pools': pools, 'keep': keep})
for keep in [0, 2]:
    cases.append({'depth': 1, 'pools': [0], 'keep': keep, 'terminal_quote_unknown': True})
for flag in ['complete', 'mayhem']:
    cases.append({'depth': 2, 'pools': [], 'keep': 0, flag: True})
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
paths = [Path(__file__), H / 'pump_nested_general_differential.py', H / 'pump_create_nested_fixture.py', H / 'proposal_common.py', a.candidate, ROOT / 'evidence/original/pump/deployed.so']
before = {str(path): sha(path) for path in paths}
rows = []
for case in cases:
    child, layout = f.fixture({'id': 'tail', 'depth': case['depth'], 'pool_positions': case['pools'], 'pool_adjustment': 0, 'asymmetric': False, 'expected': 'success'})
    child['extra_remaining'] = child['extra_remaining'][:case['keep']]
    key = layout['groups_nearest_first'][0][0]
    record = child['bootstrap_accounts'][key]
    data = bytearray.fromhex(record['data'])
    if case.get('terminal_quote_unknown'): data[83:115] = bytes([199]) * 32
    if case.get('complete'): data[48] = 1
    if case.get('mayhem'): data[81] = 1
    record['data'] = data.hex()
    x, y = f.h.run(child), f.h.run(child, a.candidate)
    assert x['transaction_base64'] == y['transaction_base64']
    assert x['verified_signature_count'] == y['verified_signature_count'] == 2
    assert not any(' invoke [' in line and (line.startswith('Program MAyhSmz') or line.startswith('Program pAMM')) for result in [x, y] for line in result['logs'])
    diff = [key for key in ['before', 'after', 'error', 'events', 'inner', 'return'] if x[key] != y[key]]
    if f.logs_for_comparison(x['logs']) != f.logs_for_comparison(y['logs']): diff.append('semantic_logs')
    rows.append({'case': case, 'original': x, 'candidate': y, 'different_fields': diff})
    print(case, x['error'], y['error'], diff, flush=True)
assert before == {str(path): sha(path) for path in paths}
report = {'scope': __doc__, 'candidate_sha256': sha(a.candidate), 'input_sha256': before, 'case_count': len(rows), 'cases': rows, 'mismatches': [row['case'] for row in rows if row['different_fields']]}
a.output.write_bytes(gzip.compress(json.dumps(report, separators=(',', ':')).encode(), mtime=0))
print('cases', len(rows), 'mismatches', len(report['mismatches']))
