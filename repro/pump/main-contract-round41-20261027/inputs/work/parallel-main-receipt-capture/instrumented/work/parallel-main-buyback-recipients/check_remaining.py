"""Signed local remaining-account cases for update_buyback_config."""
import argparse
import sys
import gzip
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parents[2] / 'scripts/pump_validate_config_admin.py'
sys.path.insert(0,str(BASE.parent))
source = BASE.read_text().split('\np=argparse.ArgumentParser', 1)[0]
source = source.replace('def execute(binary, instruction, arg, mutation):',
                        'def execute(binary, instruction, arg, mutation, remaining_keys=()):')
needle = "    if mutation == 'missing_event': metas = metas[:2]"
assert source.count(needle) == 1
source = source.replace(needle, "    for key in remaining_keys:\n        if key not in [Pubkey.default(), PROGRAM]: vm.set_account(key, Account(10**10, b'', Pubkey.default()))\n    metas.extend(AccountMeta(key, False, False) for key in remaining_keys)\n" + needle)
namespace = {'__file__': str(BASE)}
exec(compile(source, str(BASE), 'exec'), namespace)
execute, Pubkey = namespace['execute'], namespace['Pubkey']

parser = argparse.ArgumentParser()
parser.add_argument('--candidate', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--probe', action='store_true')
args = parser.parse_args()
none, some = b'\0', b'\1' + struct.pack('<Q', 1000)
valid = [Pubkey(bytes([50 + i]) * 32) for i in range(11)]
specs = []
for payload_name, payload in [('none', none), ('some', some)]:
    for count in range(11):
        specs.append((f'{payload_name}/count_{count}', payload, valid[:count]))
    for index in range(8):
        keys = valid[:8].copy(); keys[index] = Pubkey.default()
        specs.append((f'{payload_name}/zero_{index}', payload, keys))
    for left in range(8):
        for right in range(left + 1, 8):
            keys = valid[:8].copy(); keys[right] = keys[left]
            specs.append((f'{payload_name}/duplicate_{left}_{right}', payload, keys))
    keys = valid[:8].copy(); keys[0] = keys[1]; keys[7] = Pubkey.default()
    specs.append((f'{payload_name}/duplicate_and_zero', payload, keys))
for count in [0, 1, 8, 9]:
    specs.append((f'invalid_bps/count_{count}', b'\1' + struct.pack('<Q', 10001), valid[:count]))
if args.probe:
    chosen = {'none/count_1', 'none/count_8', 'none/zero_0', 'none/duplicate_0_1', 'some/count_8', 'invalid_bps/count_8'}
    specs = [spec for spec in specs if spec[0] in chosen]
fields = ['error', 'data_hex', 'lamports', 'payer_lamports', 'authority_lamports', 'event_payloads', 'inner_instructions']
cases = []
for name, payload, keys in specs:
    original = execute(ROOT / 'evidence/original/pump/deployed.so', 'update_buyback_config', payload, 'none', keys)
    candidate = execute(args.candidate, 'update_buyback_config', payload, 'none', keys)
    cases.append({'name': name, 'different_fields': [key for key in fields if original[key] != candidate[key]],
                  'original': original, 'candidate': candidate})
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = {'scope': __doc__, 'candidate_sha256': sha(args.candidate),
          'original_sha256': sha(ROOT / 'evidence/original/pump/deployed.so'),
          'fixture_sha256': sha(Path(__file__)), 'base_fixture_sha256': sha(BASE),
          'case_count': len(cases), 'mismatches': [index for index, case in enumerate(cases) if case['different_fields']], 'cases': cases}
args.output.write_bytes(gzip.compress(json.dumps(report, indent=2).encode(), mtime=0))
print(len(cases), [(case['name'], case['different_fields'], case['original']['error'], case['candidate']['error']) for case in cases if case['different_fields']])
if report['mismatches']:
    raise SystemExit(1)
