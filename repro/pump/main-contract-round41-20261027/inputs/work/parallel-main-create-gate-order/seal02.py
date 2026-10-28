from pathlib import Path
import difflib
import gzip
import hashlib
import json

root = Path(__file__).resolve().parents[2]
work = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())
plan = read(work / 'PLAN02.json')
source = Path(plan['source'])
baseline = root / 'work/parallel-main-integration/round26-source/programs/pump'
assert all(sha(Path(plan['baseline']) / k) == v for k, v in plan['baseline_files'].items())
assert all(sha(source / k) == v for k, v in plan['source_files'].items())
changed = [str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and sha(p) != sha(baseline / p.relative_to(source))]
assert changed == ['src/create_v2.rs'], changed
patch = work / 'create-gate-order-from-round26.patch'
patch.write_text(''.join(difflib.unified_diff((baseline / changed[0]).read_text().splitlines(True), (source / changed[0]).read_text().splitlines(True), fromfile='a/programs/pump/' + changed[0], tofile='b/programs/pump/' + changed[0])))
build = read(work / 'build02/build-comparison.json')
runtime = read(work / 'runtime02/summary.json')
delta = read(work / 'result02/MATCH-DELTA.json')
assert build['returncode'] == 0 and build['source_unchanged']
assert sha(work / 'build02/candidate.so') == build['comparison']['candidate_sha256'] == runtime['candidate_sha256']
assert sha(work / 'build02/unstripped.so') == build['unstripped_sha256']
assert runtime['case_count'] == 645 and not runtime['errors']
assert runtime['diagnostics']['log_bearing_cases'] == 643 and not runtime['diagnostics']['mismatches']
assert all(not x['gains'] and not x['losses'] for x in delta['sets'].values())
assert delta['retained_historical_leafs'] and delta['retained_creation_context_and_cpi']
cohorts = [
    ('before', 'create_gate_order'),
    ('control-before', 'create_control_gate_order'),
    ('policy-before', 'create_policy_precedence'),
    ('early-pairs-before', 'create_early_pairs'),
]
before_cases = before_gaps = 0
records = []
for before_name, after_name in cohorts:
    before_path = work / (before_name + '.json.gz')
    after_path = work / 'runtime02' / (after_name + '.json.gz')
    before, after = read(before_path), read(after_path)
    assert not after['mismatches']
    assert len(before['cases']) == len(after['cases'])
    assert all(row['verified_signature_count'] == 2 for row in before['cases'] + after['cases'])
    assert [x['case'] for x in before['cases']] == [x['case'] for x in after['cases']]
    before_cases += before['case_count']
    before_gaps += len(before['mismatches'])
    records.append({'name': after_name, 'cases': before['case_count'], 'before_mismatches': before['mismatches'], 'after_mismatches': after['mismatches'], 'before_sha256': sha(before_path), 'after_sha256': sha(after_path)})
assert before_cases == 60 and before_gaps == 40
paths = [work / p for p in ['PLAN01.json', 'PLAN02.json', 'STATIC-AND-BEFORE.json', 'original-entry.asm', 'original-mode-branches.asm', 'manifest02.json', 'focused-manifest02.json', 'probe_gates.py', 'probe_control_gates.py', 'probe_policy_precedence.py', 'probe_early_pairs.py', 'cases.json', 'control-cases.json', 'policy-precedence-cases.json', 'early-pairs-cases.json', 'create_fixture.py', 'nested_fixture.py', 'runtime01/summary.json', 'runtime02/summary.json', 'build02/build-comparison.json', 'result02/MATCH-DELTA.json']]
report = {
    'scope': 'Main-owned CreateV2 handler gate ordering and quote policy; companion CPI interface and implementation unchanged.',
    'source_directory': str(source),
    'compiled_source_directory': build['source_directory'],
    'source_create_v2_sha256': sha(source / 'src/create_v2.rs'),
    'baseline_create_v2_sha256': sha(baseline / 'src/create_v2.rs'),
    'patch': str(patch), 'patch_sha256': sha(patch),
    'candidate_sha256': sha(work / 'build02/candidate.so'),
    'unstripped_sha256': sha(work / 'build02/unstripped.so'),
    'source_unchanged': build['source_unchanged'],
    'changes': [
        'For Mayhem mode, compare mayhem_mode_enabled to true first and retain Left/Right bool diagnostics.',
        'Then validate cashback, holder-reward selection, nonzero creator, and create_v2_enabled, in original order.',
        'Apply the Mayhem quote restriction after quote/control selection and ATA creation, only to nonnative unlisted quote mints.',
    ],
    'new_cases': before_cases, 'before_mismatches': before_gaps, 'after_mismatches': 0,
    'cohorts': records,
    'validation': {'cases': runtime['case_count'], 'strict_log_pairs': runtime['diagnostics']['log_bearing_cases'], 'runtime_errors': runtime['errors'], 'diagnostic_mismatches': runtime['diagnostics']['mismatches'], 'new_case_signature_count_each': 2},
    'full_match_delta': delta,
    'exact_match_claim': '721 normalized / 123 raw retained, with zero gains or losses; no whole-ELF identity claim.',
    'limitations': ['Mayhem success-path fixtures reach the unchanged captured companion CPI, then stop with its missing-fixture-state error3012. This proves the main caller ordering and invoked CPI path, not a reconstructed companion or complete Mayhem success.', 'Diagnostic comparison excludes source file/line coordinates and compute usage. This focused corpus is not the parent full-checkpoint corpus.'],
    'evidence_sha256': {str(p.relative_to(root)): sha(p) for p in paths},
}
output = work / 'CREATE-GATE-ORDER-REVIEW.json'
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['source_create_v2_sha256', 'patch_sha256', 'candidate_sha256', 'unstripped_sha256', 'validation']}, indent=2))
print('review_sha256', sha(output))
print('focused_manifest_sha256', sha(work / 'focused-manifest02.json'))
