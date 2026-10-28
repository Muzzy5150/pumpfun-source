"""Signed legacy creator-vault rent boundaries; immutable fixture inputs."""
from pathlib import Path
import argparse, gzip, hashlib, json, sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'work/parallel-main-loader-optimized'))
sys.path.insert(0, str(ROOT / 'work/parallel-main-v3-buyback-assert'))
import pump_captured_loader as loader
loader.install()
import pump_legacy_buy_differential as buy
import pump_legacy_sell_differential as sell
from solders.rent import Rent
from pump_diagnostic_audit import audit
from audit_invocations import audit_invocations

for fixture in (buy, sell):
    creator = fixture.f.Pubkey(fixture.INITIAL[fixture.CURVE].data[49:81])
    vault = fixture.f.Pubkey.find_program_address([b'creator-vault', bytes(creator)], fixture.P)[0]
    assert fixture.INITIAL.get(vault) is None
    fixture.INITIAL[vault] = fixture.f.Account(10**7, b'', fixture.f.Pubkey.default())

def cases():
    minimum = Rent.default().minimum_balance(0)
    for kind in ('buy', 'buy_exact_sol_in', 'sell'):
        for mode in ('fee', 'zero_fee', 'cashback'):
            for balance in (0, 1, minimum - 1, minimum, minimum + 1):
                case = {'name': f'{kind}_{mode}_{balance}', 'kind': kind,
                        'amount': 500000000, 'minimum': 1 if kind == 'buy_exact_sol_in' else 0 if kind == 'sell' else 10**12,
                        'account_mutations': {'creator_vault': {'lamports': balance}}}
                if mode == 'zero_fee':
                    case['account_mutations']['fee_config'] = {'u64': [[101, 0]]}
                    case['curve_u64'] = [[115, 0]]
                if mode == 'cashback':
                    case['curve_bytes'] = [[82, 1]]
                    if kind == 'sell':
                        case['cashback_account'] = True
                yield case

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    rows = []
    for case in cases():
        fixture = sell if case['kind'] == 'sell' else buy
        start = len(loader.LOADS)
        original = fixture.run(case)
        candidate = fixture.run(case, a.candidate)
        loads = loader.LOADS[start:]
        assert len(loads) == 2
        diff = [k for k in ('error', 'accounts', 'events', 'inner', 'return_data') if original[k] != candidate[k]]
        rows.append({'case': case, 'original': original, 'candidate': candidate, 'different_fields': diff, 'loader': loads})
        if diff:
            print(json.dumps({'name': case['name'], 'diff': diff, 'original': original['error'], 'candidate': candidate['error']}), flush=True)
    report = {'suites': {'vault_rent': rows}, 'case_count': len(rows),
              'mismatches': [i for i, row in enumerate(rows) if row['different_fields']],
              'candidate_sha256': hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    report['diagnostics'] = audit(report['suites'])
    report['invocations'] = audit_invocations(report)
    a.output.write_bytes(gzip.compress(json.dumps(report).encode(), mtime=0))
    print(json.dumps({'cases': len(rows), 'mismatches': len(report['mismatches']),
                      'diagnostic_mismatches': len(report['diagnostics']['mismatches']),
                      'invocation_mismatches': len(report['invocations']['mismatches'])}), flush=True)

if __name__ == '__main__':
    main()
