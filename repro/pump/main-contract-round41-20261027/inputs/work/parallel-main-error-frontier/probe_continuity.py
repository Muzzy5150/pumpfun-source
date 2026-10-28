"""Normally signed route continuity through unchanged captured AMM and main Pump."""
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
for sell in [False, True]:
    for mode in ['control', 'source', 'destination', 'both']:
        def mutate(vm, metas):
            for index, role in [(1, 'source'), (2, 'destination')]:
                if mode not in [role, 'both']:
                    continue
                key = metas[index].pubkey
                account = vm.get_account(key)
                data = bytearray(account.data)
                data[:32] = bytes([77 + index]) * 32
                vm.set_account(key, h.Account(account.lamports, bytes(data), account.owner))
        x = invoke(sell, 10**6, 'exotic', 1, mutation=mutate)
        y = invoke(sell, 10**6, 'exotic', 1, a.candidate, mutation=mutate)
        assert x['transaction_base64'] == y['transaction_base64']
        assert x['verified_signature_count'] == y['verified_signature_count'] == 1
        diff = [key for key in ['error', 'events', 'inner', 'return_data', 'before', 'after', 'pump_calls', 'token_calls'] if x[key] != y[key]]
        if logs(x) != logs(y): diff.append('semantic_logs')
        rows.append({'case': {'sell': sell, 'mutation': mode}, 'original': x, 'candidate': y, 'different_fields': diff})
        print(sell, mode, x['error'], y['error'], 'pump calls', len(x['pump_calls']), diff, flush=True)
assert before == {str(p): sha(p) for p in inputs}
result = {'scope': __doc__, 'candidate_sha256': sha(a.candidate), 'input_sha256': before,
          'transformed_invoke_sha256': hashlib.sha256(source.encode()).hexdigest(),
          'case_count': len(rows), 'cases': rows,
          'mismatches': [r['case'] for r in rows if r['different_fields']]}
a.output.write_bytes(gzip.compress(json.dumps(result, separators=(',', ':')).encode(), mtime=0))
print('cases', len(rows), 'mismatches', len(result['mismatches']))
