"""Normally signed later-hop Pump account errors through unchanged captured AMM."""
from pathlib import Path
import argparse
import base64
import gzip
import hashlib
import importlib.util
import inspect
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
H = ROOT / 'work/pump-tokenkeg-two-curve-recovery/ordinary_two_curve.py'
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('continuity_fixture', H)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
source = inspect.getsource(h.invoke).replace('candidate=None):', 'candidate=None,mutation=None):')
source = source.replace('vm=LiteSVM().with_transaction_history(0)', 'vm=LiteSVM().with_transaction_history(0).with_sigverify(True)')
needle = ' def snapshot():'
assert source.count(needle) == 1
source = source.replace(needle, ' if mutation:mutation(vm,metas)\n' + needle)
namespace = dict(h.__dict__)
exec(compile(source, str(Path(__file__)), 'exec'), namespace)
invoke = namespace['invoke']
p = argparse.ArgumentParser()
p.add_argument('--candidate', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
inputs = [Path(__file__), H, H.parent / 'base-fixture.json', a.candidate, ROOT / 'evidence/original/pump/deployed.so']
before = {str(p): sha(p) for p in inputs}
def logs(result):
    return [re.sub(r'AnchorError thrown in [^\n]+?:\d+\.', 'AnchorError thrown in <source>.', line)
            for line in result['logs'] if not re.fullmatch(r'Program \S+ consumed \d+ of \d+ compute units', line)]
rows = []
cases = []
for target in ['A', 'B']:
    for mutation in ['discriminator', 'short', 'mayhem', 'readonly']:
        cases.append({'target': target, 'mutation': mutation})
cases += [{'target': 'both', 'mutation': 'discriminator'}, {'target': 'A_mayhem_B_short', 'mutation': 'mixed'}]
for case in cases:
    def mutate(vm, metas):
        targets = ['A', 'B'] if case['target'] in ['both', 'A_mayhem_B_short'] else [case['target']]
        for target in targets:
            key = h.C_A if target == 'A' else h.C_B
            mutation = ('mayhem' if target == 'A' else 'short') if case['mutation'] == 'mixed' else case['mutation']
            account = vm.get_account(key)
            data = bytearray(account.data)
            if mutation == 'discriminator': data[0] ^= 255
            if mutation == 'short': data = data[:7]
            if mutation == 'mayhem': data[81] = 1
            if mutation == 'readonly':
                for i, meta in enumerate(metas):
                    if meta.pubkey == key: metas[i] = h.AccountMeta(key, meta.is_signer, False)
            vm.set_account(key, h.Account(account.lamports, bytes(data), account.owner))
    x = invoke(False, 10**6, 'exotic', 1, mutation=mutate)
    y = invoke(False, 10**6, 'exotic', 1, a.candidate, mutation=mutate)
    assert x['transaction_base64'] == y['transaction_base64']
    assert x['verified_signature_count'] == y['verified_signature_count'] == 1
    diff = [key for key in ['error', 'events', 'inner', 'return_data', 'before', 'after', 'pump_calls', 'token_calls'] if x[key] != y[key]]
    if logs(x) != logs(y): diff.append('semantic_logs')
    rows.append({'case': case, 'original': x, 'candidate': y, 'different_fields': diff})
    print(case, x['error'], y['error'], 'pump calls', len(x['pump_calls']), diff, flush=True)
assert before == {str(p): sha(p) for p in inputs}
result = {'scope': __doc__, 'candidate_sha256': sha(a.candidate), 'input_sha256': before,
          'transformed_invoke_sha256': hashlib.sha256(source.encode()).hexdigest(),
          'case_count': len(rows), 'cases': rows,
          'mismatches': [r['case'] for r in rows if r['different_fields']]}
a.output.write_bytes(gzip.compress(json.dumps(result, separators=(',', ':')).encode(), mtime=0))
print('cases', len(rows), 'mismatches', len(result['mismatches']))
