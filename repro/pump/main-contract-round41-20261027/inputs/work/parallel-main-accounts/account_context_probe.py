#!/usr/bin/env python3
"""Signed malformed-owner and truncated-curve counterexamples."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import pump_set_creator_differential as creator
import pump_migrate_probe as migration
import pump_legacy_sell_differential as legacy
from validate_scoped import error_messages


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    rows = []
    cases = []
    for op in ['set_creator', 'set_metaplex_creator']:
        cases.append(('creator', creator.run, {'op': op, 'name': op + '-token22-owner', 'accounts': {'mint': {'owner': str(migration.T22)}}}))
    for names, owner in [(['mint'], migration.T22), (['associated_bonding_curve'], migration.T22), (['mint', 'associated_bonding_curve'], migration.T22), (['mint'], migration.Pubkey.default()), (['associated_bonding_curve'], migration.Pubkey.default())]:
        cases.append(('migration', migration.run, {'boost': True, 'name': '-'.join(names) + '-owner-' + str(owner), 'mutations': {name: {'owner': str(owner)} for name in names}}))
    for length in [49, 50, 73, 80, 81, 82, 83, 114, 115, 123, 124, 125, 140, 141, 165, 166]:
        cases.append(('legacy', legacy.run, {'name': 'curve-length-' + str(length), 'account_mutations': {'bonding_curve': {'length': length}}}))
    excluded = {'logs', 'transaction_base64'}
    for family, run, c in cases:
        x, y = run(c), run(c, a.candidate)
        fields = sorted(set(x) & set(y) - excluded)
        diff = [k for k in fields if x[k] != y[k]]
        xd, _ = error_messages(x)
        yd, _ = error_messages(y)
        if xd != yd:
            diff.append('error_messages_and_compared_values')
        rows.append({'family': family, 'case': c, 'original': x, 'candidate': y, 'different_fields': diff})
        if diff:
            print(family, c['name'], diff, flush=True)
    report = {'scope': 'Signed offline owner/context and truncated-curve probes with full compared-value diagnostics; original main ELF is the oracle.', 'original_sha256': hashlib.sha256((ROOT / 'evidence/original/pump/deployed.so').read_bytes()).hexdigest(), 'candidate_sha256': hashlib.sha256(a.candidate.read_bytes()).hexdigest(), 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'case_count': len(rows), 'cases': rows, 'mismatches': [i for i, r in enumerate(rows) if r['different_fields']]}
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    print('cases', len(rows), 'mismatches', report['mismatches'])
    return bool(report['mismatches'])


if __name__ == '__main__':
    raise SystemExit(main())
