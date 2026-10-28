from pathlib import Path
import base64,gzip,hashlib,json
from solders.transaction import VersionedTransaction
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;G=R/'work/parallel-main-unobserved-gates'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.load(gzip.open(p,'rt'))
def rows(d):return[x for v in d['suites'].values()for x in v]
new=load(P/'after01.json.gz');reg=load(P/'regression01.json.gz');before=load(G/'cashback01.json.gz');txs=loads=0
for r in rows(new)+rows(reg):
 assert not r['different_fields']
 for side in ['original','candidate']:assert all(VersionedTransaction.from_bytes(base64.b64decode(r[side]['transaction_base64'])).verify_with_results());txs+=1
 assert len(r['loader'])==2;loads+=len(r['loader'])
assert not new['diagnostics']['mismatches']and not reg['diagnostics']['mismatches']
def fingerprint(r):return hashlib.sha256(json.dumps([r['original']['transaction_base64'],r['original'].get('before')],sort_keys=True).encode()).hexdigest()
prior={fingerprint(x)for x in rows(reg)};seen=set();duplicates=[]
for r in rows(new):
 f=fingerprint(r)
 if f in prior:duplicates.append(r['case']['name'])
 seen.add(f)
byname={r['case']['name']:r for r in rows(new)};evidence=[]
for b in rows(before):
 if not b['different_fields']:continue
 a=byname[b['case']['name']];evidence.append({'case':b['case'],'original_error':b['original']['error'],'before_candidate_error':b['candidate']['error'],'after_candidate_error':a['candidate']['error'],'original_invoke_order':[x for x in b['original']['logs']if' invoke ['in x],'after_invoke_order':[x for x in a['candidate']['logs']if' invoke ['in x]})
(P/'ERROR-ORDER-EVIDENCE.json').write_text(json.dumps(evidence,indent=2)+'\n')
build=json.load(open(P/'build01/build-comparison.json'));stage=json.load(open(P/'STAGING.json'));base=R/stage['base'];source=P/'source01';actual={str(x.relative_to(source)):sha(x)for x in source.rglob('*')if x.is_file()and(x.suffix=='.rs'or x.name in ['Cargo.toml','Cargo.lock'])};basehash={str(x.relative_to(base)):sha(x)for x in base.rglob('*')if x.is_file()and(x.suffix=='.rs'or x.name in ['Cargo.toml','Cargo.lock'])};assert [x for x in actual if actual[x]!=basehash.get(x)]==['src/sell.rs'];assert sha(source/'src/sell.rs')==stage['source_sell_sha256'];assert build['primary_source_sha256'][str((source/'src/sell.rs').relative_to(R))]==stage['source_sell_sha256']
cli={'script':'work/parallel-main-unobserved-gates/probe.py','script_sha256':sha(G/'probe.py'),'args':['--family','cashback_accounts','--candidate','CANDIDATE','--output','OUTPUT.json.gz'],'raw_cases':22,'intra_matrix_unique_observable_fixtures':len(seen),'overlap_with_focused143':duplicates,'new_unique_observable_fixtures_vs_focused143':len(seen-prior),'fingerprint':'original transaction bytes and recorded complete before-account snapshot; does not prove globally unique tests'};(P/'CLI-MANIFEST.json').write_text(json.dumps(cli,indent=2)+'\n')
report={'status':'frozen validated narrow patch','base':stage['base'],'modified_files':['src/sell.rs'],'source_sha256':stage['source_sell_sha256'],'candidate_sha256':build['comparison']['candidate_sha256'],'unstripped_sha256':build['unstripped_sha256'],'paired_cases':new['case_count']+reg['case_count'],'new_matrix_cases':22,'focused_regression_cases':143,'strict_log_cases':new['diagnostics']['log_bearing_cases']+reg['diagnostics']['log_bearing_cases'],'signed_transactions_verified':txs,'paired_program_loads_verified':loads,'before_differences':len(evidence),'after_differences':0,'window_delta':json.load(open(P/'WINDOW-DELTA.json')),'inventory':json.load(open(P/'inventory.json'))['counts'],'patch':'sell-cashback-order.patch','new_case_cli':'CLI-MANIFEST.json','source_change':'Read the first cashback remaining account or return6072; validate it as the accumulator before the existing V2 lookup. Fee/base CPI order retained.'};(P/'FINAL-RESULT.json').write_text(json.dumps(report,indent=2)+'\n');(P/'SEALED.md').write_text('Source01 and all receipts are frozen. Only src/sell.rs differs from frozenR26. New22+focused143signedcasespass;4priorerror-orderdifferencesresolved. No byte-windowgain/loss;721/123. SeeFINAL-RESULT.jsonandCLI-MANIFEST.json.\n');print(json.dumps(report,indent=2))
