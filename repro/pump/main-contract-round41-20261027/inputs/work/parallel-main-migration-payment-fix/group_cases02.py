from pathlib import Path
import hashlib
import json

root = Path.cwd()
folder = root / 'work/parallel-main-migration-payment-fix'
old_path = root / 'work/parallel-main-migration-payment-alias/DEDUPLICATED-SPECS.json'
negative_path = folder / 'NEGATIVE-SPECS02.json'
records = []
for bucket, path in [('policy_funding', old_path), ('negative_cardinality', negative_path)]:
    for row in json.loads(path.read_text())['specs']:
        case = row['case']
        mode = 'funded' if 'funded_boost_lamports' in case else 'extra' if 'actual_remaining_count' in case else 'plain'
        records.append({
            'case': case, 'input_hash': row['input_hash'],
            'module': 'pump_migrate_probe' if case['name'].startswith('legacy') else 'pump_migrate_v2_probe',
            'mode': mode, 'source_bucket': bucket,
        })
assert len(records) == len({r['input_hash'] for r in records}) == 465
records.sort(key=lambda row: row['input_hash'])
groups = []
start = 0
for index in range(8):
    count = 59 if index == 0 else 58
    group_rows = records[start:start + count]
    start += count
    groups.append({'group': index + 1, 'case_count': count, 'cases': group_rows})
assert start == 465
report = {
    'scope': 'Additional migration cases deduplicated by signed transaction and canonical non-null original before accounts against the existing migration corpus and each other.',
    'case_count': 465, 'groups': groups, 'old_suite_count': 1192,
    'source_packets': {
        '36_case_spec': hashlib.sha256(old_path.read_bytes()).hexdigest(),
        '429_case_spec': hashlib.sha256(negative_path.read_bytes()).hexdigest(),
    },
}
(folder / 'MIGRATION-CASE-GROUPS02.json').write_text(json.dumps(report, indent=2) + '\n')
print([group['case_count'] for group in groups])
