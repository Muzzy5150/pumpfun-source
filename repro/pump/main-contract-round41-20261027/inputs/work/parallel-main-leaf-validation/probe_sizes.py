"""Signed migration probes for the main-owned required account-size scanner."""
from pathlib import Path
import argparse
import base64
import gzip
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import pump_migrate_v2_probe as fixture
from solders.transaction import VersionedTransaction

p = argparse.ArgumentParser()
p.add_argument('--candidate', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
mint = bytearray(82)
mint[44] = 6
mint[45] = 1
def tlv(kind, value):
    return kind.to_bytes(2, 'little') + len(value).to_bytes(2, 'little') + value
def extended(entries, tail=b''):
    return bytes(mint) + bytes(83) + b'\x01' + b''.join(tlv(k, v) for k, v in entries) + tail

definitions = [
    ('plain', bytes(mint)),
    ('empty_extended', extended([], b'\0\0')),
    ('single_byte_tail', extended([], b'\0')),
    ('unknown_kind_99', extended([(99, b'')])),
    ('unknown_kind_65535', extended([(65535, bytes(8))])),
    ('mint_close_authority', extended([(3, bytes(32))])),
    ('duplicate_mint_close', extended([(3, bytes(32)), (3, bytes(32))])),
    ('pausable_config', extended([(26, bytes(33))])),
    ('duplicate_pausable', extended([(26, bytes(33)), (26, bytes(33))])),
    ('transfer_hook_unset', extended([(14, bytes(64))])),
    ('duplicate_transfer_hook', extended([(14, bytes(64)), (14, bytes(64))])),
    ('transfer_fee_zero', extended([(1, bytes(108))])),
    ('duplicate_transfer_fee', extended([(1, bytes(108)), (1, bytes(108))])),
    ('fee_payload_extra', extended([(1, bytes(112))])),
]
cases = []
for name, data in definitions:
    c = {'case': name, 'boost': True, 'stable': True, 'quote22': True,
         'writable': ['quote_mint'],
         'mutations': {'quote_mint': {'patches': [(0, data.hex())]}}}
    if 'transfer_fee' in name or 'fee_payload' in name:
        q = fixture.Pubkey.from_bytes(bytes([217]) * 32)
        curve = fixture.pda([b'bonding-curve', bytes(fixture.MINT)], fixture.P)
        account = bytearray(165)
        account[:32], account[32:64] = bytes(q), bytes(curve)
        account[64:72] = (85005359063).to_bytes(8, 'little')
        account[108] = 1
        c['mutations']['associated_quote_bonding_curve'] = {'patches': [(0, (bytes(account) + b'\x02' + tlv(2, bytes(8))).hex())]}
    cases.append(c)

sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
inputs = [Path(__file__), Path(fixture.__file__), a.candidate, ROOT / 'evidence/original/pump/deployed.so']
before = {str(p): sha(p) for p in inputs}
def logs(x):
    return [re.sub(r'AnchorError thrown in [^\n]+?:\d+\.', 'AnchorError thrown in <source>.', line)
            for line in x['logs'] if not re.fullmatch(r'Program \S+ consumed \d+ of \d+ compute units', line)]
rows = []
for c in cases:
    x, y = fixture.run(c), fixture.run(c, a.candidate)
    assert x['transaction_base64'] == y['transaction_base64']
    tx = VersionedTransaction.from_bytes(base64.b64decode(x['transaction_base64']))
    assert all(tx.verify_with_results()) and len(tx.signatures) == 2
    diff = [key for key in ['error', 'before', 'after', 'inner', 'return'] if x[key] != y[key]]
    if logs(x) != logs(y): diff.append('semantic_logs')
    rows.append({'case': c, 'original': x, 'candidate': y, 'different_fields': diff, 'verified_signature_count': 2})
    print(c['case'], x['error'], y['error'], diff, flush=True)
assert before == {str(p): sha(p) for p in inputs}
result = {'scope': __doc__, 'candidate_sha256': sha(a.candidate), 'input_sha256': before,
          'case_count': len(rows), 'cases': rows,
          'mismatches': [r['case']['case'] for r in rows if r['different_fields']]}
a.output.write_bytes(gzip.compress(json.dumps(result, separators=(',', ':')).encode(), mtime=0))
print('cases', len(rows), 'mismatches', len(result['mismatches']))
