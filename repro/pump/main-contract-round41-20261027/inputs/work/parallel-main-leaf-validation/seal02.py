from pathlib import Path
import difflib
import gzip
import hashlib
import json

root = Path(__file__).resolve().parents[2]
work = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())
plan1, plan2 = read(work / 'PLAN01.json'), read(work / 'PLAN02.json')
base, source = Path(plan1['baseline']), Path(plan2['source'])
assert all(sha(base / k) == v for k, v in plan1['baseline_files'].items())
assert all(sha(source / k) == v for k, v in plan2['source_files'].items())
changed = [str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and sha(p) != sha(base / p.relative_to(source))]
assert changed == ['src/migrate_v2.rs'], changed
patch = work / 'migrate-pausable-from-round27.patch'
patch.write_text(''.join(difflib.unified_diff((base / changed[0]).read_text().splitlines(True), (source / changed[0]).read_text().splitlines(True), fromfile='a/programs/pump/' + changed[0], tofile='b/programs/pump/' + changed[0])))
build = read(work / 'build02/build-comparison.json')
runtime = read(work / 'runtime02/summary.json')
delta = read(work / 'result02/MATCH-DELTA.json')
assert build['returncode'] == 0 and build['source_unchanged']
assert sha(work / 'build02/candidate.so') == build['comparison']['candidate_sha256'] == runtime['candidate_sha256']
assert sha(work / 'build02/unstripped.so') == build['unstripped_sha256']
assert runtime['case_count'] == 1192 and not runtime['errors'] and not runtime['diagnostics']['mismatches']
assert all(not x['gains'] and not x['losses'] for x in delta['sets'].values())
assert delta['retained_historical_leafs'] and delta['retained_creation_context_and_cpi']
counts = []
for before_name, after_name in [('sizes-before01', 'required_account_size'), ('pausable-before01', 'pausable_migration')]:
    before_path, after_path = work / (before_name + '.json.gz'), work / 'runtime02' / (after_name + '.json.gz')
    b, a = read(before_path), read(after_path)
    assert [x['case'] for x in b['cases']] == [x['case'] for x in a['cases']]
    assert all(row['verified_signature_count'] == 2 for row in b['cases'] + a['cases'])
    assert not a['mismatches']
    counts.append({'name': after_name, 'cases': a['case_count'], 'before_mismatches': b['mismatches'], 'after_mismatches': a['mismatches'], 'before_sha256': sha(before_path), 'after_sha256': sha(after_path)})
assert sum(x['cases'] for x in counts) == 20
assert sum(len(x['before_mismatches']) for x in counts) == 6
files = ['TRIAGE.json', 'PLAN01.json', 'PLAN02.json', 'original-17c0f0.asm', 'original-17c3d8.asm', 'original-fee-wrapper.asm', 'original-account-size-call.asm', 'CALLERS.json', 'sizes-before01.json.gz', 'pausable-before01.json.gz', 'sizes-after01.json.gz', 'sizes-before01.loader.json', 'pausable-before01.loader.json', 'sizes-after01.loader.json', 'helper01.json', 'manifest.json', 'focused-manifest.json', 'probe_sizes.py', 'probe_pausable.py', 'build02/build-comparison.json', 'runtime02/summary.json', 'result01/MATCH-DELTA.json', 'result02/MATCH-DELTA.json']
dependencies = [root / 'evidence' / folder / 'deployed.so' for folder in ['original/pump', 'original/pump_amm', 'dependencies/spl_token', 'dependencies/spl_token_2022', 'dependencies/associated_token']]
report = {
    'scope': 'Main-only MigrateV2 PausableConfig compatibility in required account size and fee-presence parsing.',
    'source_directory': str(source), 'compiled_source_directory': build['source_directory'],
    'source_migrate_v2_sha256': sha(source / changed[0]), 'baseline_migrate_v2_sha256': sha(base / changed[0]),
    'patch': str(patch), 'patch_sha256': sha(patch),
    'candidate_sha256': sha(work / 'build02/candidate.so'), 'unstripped_sha256': sha(work / 'build02/unstripped.so'),
    'changes': ['Required token-account size follows original0x17c0f0 primitive TLV tags and recognizes PausableConfig26 -> required4 bytes.', 'The later transfer-fee-presence query preserves raw tags instead of rejecting26 through the older dependency enum. Base Mint unpack and declared TLV bounds are retained.'],
    'causal_control': 'Size-only source01 restored both AMM CPI operations but still failed at the later enum conversion after the first CloseAccount. It is retained as unpromoted partial evidence.',
    'new_cases': counts, 'before_mismatches': 6, 'after_mismatches': 0,
    'validation': {'cases': runtime['case_count'], 'strict_log_pairs': runtime['diagnostics']['log_bearing_cases'], 'runtime_errors': runtime['errors'], 'diagnostic_mismatches': runtime['diagnostics']['mismatches'], 'new_case_signature_count_each': 2},
    'full_match_delta': delta,
    'unchanged_captured_dependencies_sha256': {str(p.relative_to(root)): sha(p) for p in dependencies},
    'evidence_sha256': {str((work / f).relative_to(root)): sha(work / f) for f in files},
    'limitations': ['No new exact-body or whole-ELF identity claim. The source01 account-size body was1184 bytes versus original744; source structure remains recoverable work.', 'Signed fixtures use synthetic state and unchanged captured AMM/Token/Token2022/ATA programs; no companion implementation was edited.', 'Diagnostic comparisons exclude source coordinates and compute consumption.'],
    'other_leaf': {'original': '0x17c3d8/368B', 'attribution': 'TransferFee::calculate_fee', 'caller': '0x94e28/696B', 'source': 'trade_v3::quote_fee_for_amount already invokes native calculate_fee', 'change': None},
}
output = work / 'MIGRATE-PAUSABLE-REVIEW.json'
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['source_migrate_v2_sha256', 'patch_sha256', 'candidate_sha256', 'unstripped_sha256', 'validation']}, indent=2))
print('review_sha256', sha(output))
print('focused_manifest_sha256', sha(work / 'focused-manifest.json'))
