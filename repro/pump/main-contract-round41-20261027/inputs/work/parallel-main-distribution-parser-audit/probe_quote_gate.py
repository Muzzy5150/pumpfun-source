"""Normally signed V1 quote-mint admission and precedence comparisons."""
from pathlib import Path
import argparse
import base64
import gzip
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
import pump_creator_distribution_differential as fixture
from pump_diagnostic_audit import audit
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction


def cases():
    quotes = {'default': Pubkey.default(),
              'native': Pubkey.from_string('So11111111111111111111111111111111111111112'),
              'other': Pubkey.from_bytes(bytes([88]) * 32)}
    for name, quote in quotes.items():
        for fault in ['none', 'creator', 'paused', 'pending', 'remaining', 'vault_readonly', 'sharing_mint', 'event']:
            patches = [(83, bytes(quote).hex())]
            case = {'name': name + '/' + fault, 'op': 'distribute_creator_fees',
                    'direct_mutations': {'curve': {'patches': patches}}}
            if fault == 'creator':
                patches.append((49, bytes(fixture.OTHER.pubkey()).hex()))
            if fault == 'paused':
                case['status'] = 0
            if fault == 'pending':
                patches.append((125, (1).to_bytes(8, 'little').hex()))
            if fault == 'remaining':
                case['remaining'] = []
            if fault == 'vault_readonly':
                case['readonly'] = 'creator_vault'
            if fault == 'sharing_mint':
                case['sharing_patches'] = [(11, bytes(fixture.OTHER.pubkey()).hex())]
            if fault == 'event':
                case['wrong'] = 'event_authority'
            yield case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inputs = [Path(__file__), args.candidate, Path(fixture.__file__), fixture.ORIGINAL]
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {str(p.resolve()): digest(p) for p in inputs}
    rows = []
    for case in cases():
        original = fixture.run(case)
        candidate = fixture.run(case, args.candidate)
        assert original['transaction_base64'] == candidate['transaction_base64']
        for side in (original, candidate):
            assert all(VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
        differences = [key for key in ('error', 'before', 'after', 'events', 'inner', 'return')
                       if original[key] != candidate[key]]
        rows.append({'case': case, 'original': original, 'candidate': candidate, 'different_fields': differences})
        print(case['name'], original['error'], candidate['error'], differences, flush=True)
    assert before == {str(p.resolve()): digest(p) for p in inputs}
    report = {'scope': __doc__, 'inputs_sha256': before, 'case_count': len(rows), 'cases': rows,
              'mismatches': [row['case']['name'] for row in rows if row['different_fields']],
              'diagnostics': audit({'v1_quote_gate': rows})}
    args.output.write_bytes(gzip.compress(json.dumps(report).encode(), mtime=0))
    print(json.dumps({'cases': len(rows), 'mismatches': report['mismatches'],
                      'diagnostic_mismatches': len(report['diagnostics']['mismatches'])}))


if __name__ == '__main__':
    main()
