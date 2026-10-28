"""Replay one immutable, balanced group of added migration cases."""
from pathlib import Path
import argparse
import base64
import gzip
import hashlib
import importlib
import inspect
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFINITIONS = HERE / 'MIGRATION-CASE-GROUPS02.json'

FUNDING_INSERT = ''' if c.get('funded_boost_lamports') is not None:
  native = not c.get('stable')
  boost_key=names['boost_authority'];vault_key=names['boost_vault'];quote_key=names.get('quote_mint',names.get('wsol_mint'));balance=c['funded_boost_lamports']
  d=bytearray(165);d[:32]=bytes(quote_key);d[32:64]=bytes(boost_key);d[108]=1
  if native:
   d[64:72]=max(0,balance-2039280).to_bytes(8,'little');d[109:113]=(1).to_bytes(4,'little');d[113:121]=(2039280).to_bytes(8,'little')
  put(vault_key,Account(balance,bytes(d),qt if 'qt'in locals() else TOKEN))
'''
EXTRA_INSERT = " if c.get('actual_remaining_count',2)>2:metas += [AccountMeta(Pubkey.default(),False,False)]*(c['actual_remaining_count']-2)\n"


def fixture(record, cache, transforms):
    key = (record['module'], record['mode'])
    if key not in cache:
        module = importlib.import_module(record['module'])
        if record['mode'] == 'plain':
            cache[key] = module.run
        else:
            source = inspect.getsource(module.run)
            needle = ' def snap():'
            assert source.count(needle) == 1
            insertion = FUNDING_INSERT if record['mode'] == 'funded' else EXTRA_INSERT
            source = source.replace(needle, insertion + needle)
            namespace = dict(module.__dict__)
            exec(compile(source, str(Path(__file__)), 'exec'), namespace)
            cache[key] = namespace['run']
            transforms['/'.join(key)] = hashlib.sha256(source.encode()).hexdigest()
    return cache[key]


def run_case(record, candidate, cache, transforms):
    from solders.transaction import VersionedTransaction
    execute = fixture(record, cache, transforms)
    original = execute(record['case'])
    current = execute(record['case'], candidate)
    assert original['transaction_base64'] == current['transaction_base64']
    before = {key: value for key, value in original['before'].items() if value is not None}
    fingerprint = hashlib.sha256((original['transaction_base64'] + json.dumps(before, sort_keys=True, separators=(',', ':'))).encode()).hexdigest()
    assert fingerprint == record['input_hash']
    for side in (original, current):
        assert all(VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
    differing = [key for key in ('error', 'before', 'after', 'inner', 'return') if original[key] != current[key]]
    if [line for line in original['logs'] if line.startswith('Program data:')] != [line for line in current['logs'] if line.startswith('Program data:')]:
        differing.append('events')
    return {'case': record['case'], 'input_hash': fingerprint, 'original': original, 'candidate': current, 'different_fields': differing}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', type=int, choices=range(1, 9), required=True)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--list-only', action='store_true')
    args = parser.parse_args()
    definition = json.loads(DEFINITIONS.read_text())
    group = next(item for item in definition['groups'] if item['group'] == args.group)
    if args.list_only:
        print(json.dumps({'group': args.group, 'case_count': group['case_count'], 'input_hashes': [row['input_hash'] for row in group['cases']]}))
        return
    assert args.candidate is not None and args.output is not None
    sys.path.insert(0, str(ROOT / 'scripts'))
    sys.path.insert(0, str(ROOT / 'work/parallel-main-loader-optimized'))
    import pump_captured_loader as loader
    loader.install()
    from pump_diagnostic_audit import audit
    cache, transforms, rows = {}, {}, []
    for record in group['cases']:
        row = run_case(record, args.candidate, cache, transforms)
        rows.append(row)
        if row['different_fields']:
            print(record['case']['name'], row['different_fields'], flush=True)
    report = {
        'scope': __doc__, 'group': args.group, 'case_count': len(rows), 'cases': rows,
        'mismatches': [i for i, row in enumerate(rows) if row['different_fields']],
        'candidate_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'definition_sha256': hashlib.sha256(DEFINITIONS.read_bytes()).hexdigest(),
        'transformed_fixture_sha256': transforms, 'diagnostics': audit({'migration_group': rows}),
    }
    args.output.write_bytes(gzip.compress(json.dumps(report).encode(), mtime=0))
    print(json.dumps({'group': args.group, 'case_count': len(rows), 'mismatches': report['mismatches']}))
    assert not report['mismatches'] and not report['diagnostics']['mismatches']


if __name__ == '__main__':
    main()
