"""Signed waived/control buys crossing real reserves; no source mutation."""
from pathlib import Path
import argparse, gzip, hashlib, json, struct, sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
import pump_legacy_buy_differential as legacy
import pump_buy_v2_differential as v2
from pump_diagnostic_audit import audit

p = argparse.ArgumentParser()
p.add_argument('--candidate', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
rows = []
for module, kinds in [(legacy, ['buy', 'buy_exact_sol_in']), (v2, ['buy_v2', 'buy_exact_quote_in_v2'])]:
    reserve = struct.unpack_from('<Q', module.INITIAL[module.CURVE].data, 24)[0]
    for kind in kinds:
        for token in ([False, True] if module is v2 else [False]):
            for partial in [False, True]:
                for minimum in ([1, reserve + 1] if 'exact' in kind else [10**18]):
                    for waived in [False, True]:
                        c = {'name': f'{kind}_{token}_{partial}_{minimum}_{waived}', 'kind': kind,
                             'token_quote': token, 'amount': 10**12 if 'exact' in kind else reserve + 1,
                             'minimum': minimum, 'trailing': [int(partial)] if module is v2 else [0, int(partial)]}
                        if waived:
                            c['account_mutations'] = {'global': {'bytes': [(451+i, x) for i,x in enumerate(bytes(module.USER.pubkey()))]}}
                        begin = len(loader.LOADS)
                        o = module.run(c); n = module.run(c, a.candidate)
                        loads = loader.LOADS[begin:]
                        assert len(loads) == 2
                        diff = [k for k in ['error', 'accounts', 'events', 'inner', 'return_data'] if o[k] != n[k]]
                        rows.append({'case':c, 'original':o, 'candidate':n, 'different_fields':diff, 'loader':loads})
                        if diff:
                            print(json.dumps({'case':c['name'], 'diff':diff, 'original':o['error'], 'candidate':n['error']}), flush=True)
d = audit({'crossing':rows})
r = {'case_count':len(rows), 'suites':{'crossing':rows}, 'diagnostics':d,
     'mismatches':[i for i,x in enumerate(rows) if x['different_fields']],
     'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
     'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0))
print(json.dumps({'cases':len(rows),'mismatches':len(r['mismatches']),'strict_mismatches':len(d['mismatches'])}),flush=True)
raise SystemExit(bool(r['mismatches'] or d['mismatches']))
