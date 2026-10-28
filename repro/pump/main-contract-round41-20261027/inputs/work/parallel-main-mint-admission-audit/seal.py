from pathlib import Path
import json,gzip,hashlib,difflib
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
plan=read(W/'PLAN01.json');B=Path(plan['baseline']);S=W/'source02'
assert all(sha(B/n)==v for n,v in plan['before'].items());changed=[n for n,v in plan['before'].items()if sha(S/n)!=v];assert changed==['src/create_v2.rs']
patch=W/'pump-mint-exception-from-round31.patch';patch.write_text(''.join(difflib.unified_diff((B/changed[0]).read_text().splitlines(True),(S/changed[0]).read_text().splitlines(True),fromfile='a/programs/pump/'+changed[0],tofile='b/programs/pump/'+changed[0])))
run=read(W/'runtime02/summary.json');assert run['case_count']==601 and run['diagnostics']['log_bearing_cases']==599 and not run['errors']and not run['diagnostics']['mismatches']
before,after=read(W/'gate01.json.gz'),read(W/'gate02.json.gz');assert before['case_count']==after['case_count']==32 and len(before['mismatches'])==6 and not after['mismatches']
policy=read(W/'policy01.json.gz');assert policy['case_count']==107 and not policy['mismatches'];dedup=read(W/'DEDUPLICATION.json');assert dedup['kept_count']==58
build=read(W/'build02/build-comparison.json');control=read(W/'build03/build-comparison.json');delta=read(W/'result03/MATCH-DELTA.json');assert build['returncode']==control['returncode']==0 and build['source_unchanged']and control['source_unchanged'];assert run['candidate_sha256']==sha(W/'build02/candidate.so')==build['comparison']['candidate_sha256'];assert sha(W/'build02/unstripped.so')==build['unstripped_sha256'];assert all(not x['gains']and not x['losses']for x in delta['sets'].values());assert delta['retained_historical_leafs']and delta['retained_creation_context_and_cpi']
for b in [build,control]:assert b['primary_source_sha256'][str((S/'src/create_v2.rs').relative_to(R))]==sha(S/'src/create_v2.rs')
files=['CALLER-POLICY-PROOF.json','PLAN01.json','PLAN02.json','QUOTE-FIXTURE-DERIVATION.json','policy01.json.gz','policy01.loader.json','gate01.json.gz','gate01.loader.json','gate02.json.gz','gate02.loader.json','runtime02/summary.json','build02/build-comparison.json','build03/build-comparison.json','result02/MATCH-DELTA.json','result03/MATCH-DELTA.json','DEDUPLICATION.json','incremental-cases.json','incremental-manifest.json','probe_incremental.py','probe_policy_boundaries.py','probe_program_gate.py','quote_key_fixture.py']
report={
 'scope':'Minimal main CreateV2 PUMP quote-mint extension-admission exception. No scanner rewrite, companion or dependency source changes.',
 'source_directory':str(S),'source_create_v2_sha256':sha(S/'src/create_v2.rs'),'baseline_create_v2_sha256':sha(B/'src/create_v2.rs'),
 'patch':str(patch),'patch_sha256':sha(patch),
 'change':'Keep Token2022-only validation, but skip scanner for original literal quote mint pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn.',
 'before_after':{'matrix_cases':32,'before_differences':6,'after_differences':0,'new_original_successes_previously_rejected':4},
 'qualified_runtime':{'candidate_sha256':sha(W/'build02/candidate.so'),'unstripped_sha256':sha(W/'build02/unstripped.so'),'build':'build02','cases':601,'strict_log_pairs':599,'errors':[],'diagnostic_mismatches':[],'limits':'Two historical preflight cases have no paired runtime logs; all new58 cases execute and verify identical ordinary signed transactions.'},
 'incremental_coverage':{'raw_boundary_cases':107,'new_boundary_inputs':34,'raw_gate_cases':32,'new_gate_inputs':24,'deduplicated_new_inputs':58,'overlap_inputs':81,'normalization':dedup['scope'],'manifest':'incremental-manifest.json'},
 'window_control':{'build':'build03','candidate_sha256':sha(W/'build03/candidate.so'),'unstripped_sha256':sha(W/'build03/unstripped.so'),'baseline':'frozen R31','normalized_before':730,'normalized_after':730,'raw_before':137,'raw_after':137,'gains':[],'losses':[],'recipe':'Unchanged source02 under R31 existing ordered.ld; private preservation control only. Not a newly qualified ordering recipe for changed/composite source. Root must derive next composite order and revalidate.'},
 'preserved_source':{'scanner':'quote_extensions_supported unchanged; only direct original caller supplies true. No reachable main false-policy path claimed.','prior_deliveries':'All other R31 source files identical to frozen baseline.'},
 'evidence_sha256':{str((W/n).relative_to(R)):sha(W/n)for n in files}}
(W/'MINT-ADMISSION-REVIEW.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['source_create_v2_sha256','baseline_create_v2_sha256','patch_sha256','before_after','incremental_coverage','qualified_runtime']},indent=2));print('review_sha256',sha(W/'MINT-ADMISSION-REVIEW.json'))
