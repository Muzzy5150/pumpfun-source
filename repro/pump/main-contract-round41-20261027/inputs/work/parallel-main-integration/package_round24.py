"""Seal the verified Round24 main-Pump source, builds and bounded runtime evidence."""
from pathlib import Path
import gzip,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;P=ROOT/'repro/pump/main-contract-round24-20261027';P.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def cp(src,dst):
 out=P/dst;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,out)
full=read(W/'round24-captured-full.json.gz');extra=read(W/'round24-captured-additional.json.gz');build=read(W/'build-round24-final/build-comparison.json');inv=read(W/'build-round24-final/normalized-inventory.json');closure=read(W/'round24-closed-call-body-inventory.json');promotion=read(W/'round24-promotion.json')
assert full['case_count']==10468 and len(full['suites'])==44 and not full['mismatches'];assert extra['case_count']==6209 and extra['suite_count']==119 and not extra['diagnostics']['mismatches'];assert full['candidate_sha256']==extra['candidate_sha256']==build['comparison']['candidate_sha256']==promotion['candidate_sha256']
source={};primary={}
for mapping,base,dest,out in [(build['source_sha256'],W/'build-round24-final/source','source',source),(build['primary_source_sha256'],W/'round24-final-source/programs/pump','primary',primary)]:
 for name,digest in mapping.items():
  p=ROOT/name;rel=p.relative_to(base);assert sha(p)==digest;cp(p,Path(dest)/rel);out[str(rel)]=digest
for src,dst in [('build-round24-final/candidate.so','candidate.so'),('build-round24-final/unstripped.so','unstripped.so'),('build-round24-final/build-comparison.json','build.json'),('build-round24-final-repeat/build-comparison.json','repeat-build.json'),('round24-captured-full.json.gz','full.json.gz'),('round24-captured-additional.json.gz','additional.json.gz'),('round24-closed-call-body-inventory.json','closed-calls.json'),('round24-promotion.json','promotion.json'),('round24-integration-plan.json','integration-plan.json')]:cp(W/src,dst)
cp(ROOT/'evidence/original/pump/capture.json','target-capture.json');(P/'inventory.json.gz').write_bytes(gzip.compress((W/'build-round24-final/normalized-inventory.json').read_bytes(),mtime=0))
inputs={**full['bound_files_sha256'],**{str(ROOT/k):v for k,v in full['script_sha256'].items()},**extra['input_sha256']}
for name in ['scripts/pump_compare_function_bytes.py','scripts/pump_quote_control_function_match.py','scripts/pump_diagnostic_audit.py','scripts/pump_build_verified.py','scripts/pump_dependency_cache.py','scripts/pump_physical_source_wrapper.py','scripts/build_source_manifest.py','scripts/compare.py','scripts/pump_captured_loader.py','scripts/pump_with_captured_loader.py']:
 inputs[str(ROOT/name)]=sha(ROOT/name)
py={}
for name,digest in inputs.items():
 p=Path(name).resolve()
 try:rel=p.relative_to(ROOT)
 except ValueError:continue
 assert sha(p)==digest,(name,digest,sha(p))
 if p.suffix=='.py':cp(p,Path('inputs')/rel);py[str(rel)]=digest
loaders=[]
for group,report in [('full',full),('additional',extra)]:
 if report.get('loader_receipts'):
  files=[Path(row['path']) for row in report['loader_receipts'].values()]
 else:
  files=[Path(row['command'][row['command'].index('--receipt')+1]) for row in report['results']]
 for file in files:
  file=file if file.is_absolute()else ROOT/file
  dest=Path('loaders')/group/file.name;cp(file,dest);loaders.append(str(dest))
cache=build['dependency_cache'];manifest=Path(cache['cache_root'])/cache['key']/'MANIFEST.json';assert sha(manifest)==cache['manifest_sha256'];cp(manifest,'dependency-cache-manifest.json')
for name in ['canonical32-parity.json','negative-controls.json','key-controls.json','producer-unavailable-parity.json','public-promotion.json']:
 p=ROOT/'work/parallel-main-cache'/name
 if p.exists():cp(p,Path('cache-controls')/name)
matched=sum(x['bytes']for x in inv['windows']if x['normalized_matches']);checkpoint={'scope':__doc__,'goal_complete':False,'whole_elf_equal':False,'candidate_sha256':sha(P/'candidate.so'),'unstripped_sha256':sha(P/'unstripped.so'),'original_sha256':build['comparison']['original_sha256'],'source_sha256':source,'primary_source_sha256':primary,'input_python_sha256':py,'loader_receipts':loaders,'full_cases':10468,'full_suites':44,'full_log_cases':full['diagnostics']['log_bearing_cases'],'additional_cases':6209,'additional_suites':119,'additional_log_cases':extra['diagnostics']['log_bearing_cases'],'normalized_windows':inv['counts']['normalized'],'raw_windows':inv['counts']['raw'],'original_windows':len(inv['windows']),'matched_text_bytes':matched,'original_text_bytes':1792208,'closed_call_windows_without_data':closure['counts']['closed_call_graph_windows_without_data_references'],'archived_recipe_reproduced':False,'known_incomplete':'Full ELF, data/relocations, remaining bodies and source/build provenance remain unresolved. This checkpoint fixes legacy/V2 creator-vault funding; newly observed creator-Sweep and AdminCto rent differences are tracked for the next integration.'};(P/'CHECKPOINT.json').write_text(json.dumps(checkpoint,indent=2)+'\n')

for name in ['verify.py','reproduce.py']:
 cp(ROOT/'repro/pump/main-contract-round23-20261027'/name,name)
for directory in ['work/parallel-main-v2-helpers','work/parallel-main-v3-helpers','work/parallel-main-option-bool','work/parallel-main-v2-handlers','work/parallel-main-v2-context','work/parallel-main-legacy-sell-rent']:
 for f in (ROOT/directory).glob('*.py'):
  cp(f,Path('inputs')/f.relative_to(ROOT))

old_checkpoint=read(ROOT/'repro/pump/main-contract-round23-20261027/CHECKPOINT.json')
support={}
for name in old_checkpoint.get('supporting_python_sha256',{}):
 p=ROOT/name;cp(p,Path('inputs')/name);support[name]=sha(p)
for directory in ['work/parallel-main-fee-market-cap','work/parallel-main-sweep-prepare','work/parallel-main-sweep-quote-predicate','work/parallel-main-decode-envelope','work/parallel-main-admin-cto-rent','work/parallel-main-migrate-prepare','work/parallel-main-migrate-v2-prepare','work/parallel-main-fee-recipient-helper','work/parallel-main-global-fee-waiver','work/parallel-main-fee-waiver','work/parallel-main-sell-v2-buyback','work/parallel-main-buy-v2-order','work/parallel-main-v3-fee-waiver','work/parallel-main-v3-post-ceil','work/parallel-main-v3-validity','work/parallel-main-v3-net-budget','work/parallel-main-create-frontier','work/parallel-main-create-handlers','work/parallel-main-v3-sell-supply','work/parallel-main-create-sizing','work/parallel-main-shared-sell-transfer','work/parallel-main-buy-native-recipient','work/parallel-main-v3-fee-wrapper','work/parallel-main-migration-burn','work/parallel-main-buyback-split','work/parallel-main-legacy-buyback-split','work/parallel-main-sell-v2-buyback-accounting','work/parallel-main-v3-buyback-assert','work/parallel-main-v3-cost-order','work/parallel-main-v3-accounting-boundary']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for src,dst in [('round23-integration-plan.json','integration-base-plan.json'),('round24-check-state.json','validation-state.json')]:cp(W/src,dst)
for directory,names in [('work/parallel-main-create-frontier',['OPTION-BOOL-REVIEW.json','OUTLINED-ANCESTOR-DELIVERY.json','STATIC-METADATA-REVIEW.json']),('work/parallel-main-create-handlers',['METADATA-API-REVIEW.json','DATA-FIRST-REVIEW.json']),('work/parallel-main-buy-v2-order',['ATA-ORDER-EVIDENCE.json','summary.json','NEW-CASES.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for directory,names in [('work/parallel-main-create-handlers',['V2-METADATA-COMBINED-REVIEW.json','V2-METADATA-INIT-REVIEW.json','V2-METADATA-AUTHORITY-REVIEW.json']),('work/parallel-main-buy-v2-transfer-helper',['EXACT-EVIDENCE.json','summary.json']),('work/parallel-main-v3-sell-supply',['FULL-RESULT.json','FOCUSED-RESULT.json','EVIDENCE-MANIFEST.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
C=ROOT/'work/parallel-main-create-sizing'
for name in ['FINAL-REVIEW.json','DIRECT-TRAIT-PARITY.json','PRODUCER-INDEPENDENT.json','CACHE-ISOLATION.json']:
 cp(C/name,Path('new-cache-provenance')/name)
for label,directory in [('clean','build-direct-trait'),('cached','build-direct-trait-cached02')]:
 for name in ['candidate.so','unstripped.so','build-comparison.json']:
  cp(C/directory/name,Path('new-cache-provenance')/label/name)
for directory,names in [('work/parallel-main-buy-native-recipient',['summary.json','PANIC-ORDER-EVIDENCE.json','NEW-CASES.json']),('work/parallel-main-shared-sell-transfer',['FINAL-RESULT.json','EVIDENCE-MANIFEST.json']),('work/parallel-main-v3-fee-wrapper',['NEW-PROBE-MANIFEST.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
cp(C/'build-direct-trait/build-comparison.json','fully-clean-dependency-baseline.json')
checkpoint['repeat_build_kind']='Fresh main compilation using hash-verified external-only dependencies; the new direct-trait dependency graph was independently rebuilt without cache and reproduced using the new cache key.'
# The copied verifier already checks new-cache provenance. Add the new
# invocation-order invariant and preserve the single-queue run state.
verifier=P/'verify.py';v=verifier.read_text();needle=' from solders.transaction import VersionedTransaction'
extra=""" import importlib.util
 audit_path=P/'inputs/work/parallel-main-v3-buyback-assert/audit_invocations.py'
 audit_spec=importlib.util.spec_from_file_location('archived_invocation_audit',audit_path)
 audit_module=importlib.util.module_from_spec(audit_spec);audit_spec.loader.exec_module(audit_module)
 for report in [full,extra]:
  calls=audit_module.audit_invocations(report['suites']);assert not calls['mismatches'];assert calls['paired_cases']==report['case_count']
"""
assert v.count(needle)==1
if 'archived_invocation_audit' not in v:v=v.replace(needle,extra+needle)
partition_probe=""" ordered_windows=sorted(iv['windows'],key=lambda row:row['start'])
 cursor=os['.text']['addr']
 for row in ordered_windows:
  assert row['start']==cursor and row['bytes']>0 and row['bytes']%8==0
  cursor+=row['bytes']
 assert cursor==os['.text']['addr']+os['.text']['size']==os['.text']['addr']+cp['original_text_bytes']
"""
if 'ordered_windows=sorted' not in v:v=v.replace(" for window in iv['windows']:",partition_probe+" for window in iv['windows']:")
verifier.write_text(v)
cp(W/'round24-final-unified/state.json','queue-state.json')
for directory,names in [('work/parallel-main-migration-burn',['BURN-API-REVIEW.json','BURN-IDENTITY-EVIDENCE.json']),('work/parallel-main-legacy-buyback-split',['summary.json','NEW-CASES.json']),('work/parallel-main-sell-v2-buyback-accounting',['summary.json','NEW-CASES.json']),('work/parallel-main-v3-buyback-assert',['FINAL-RESULT02.json','EVIDENCE-MANIFEST02.json']),('work/parallel-main-v3-cost-order',['FOCUSED-RESULT.json','INCREMENTAL-CLI-MANIFEST.json']),('work/parallel-main-data-frontier',['LAYOUT-TRIAL.json','LAYOUT-RESULT.json','LAYOUT-REVIEW.json','SIGNED-LOG-SOURCE-MAPPINGS.json','SOURCE-PATHS.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for name in ['run_round24_full.py','main_corpus_runner_v2.py','finish_round24.py','package_round24.py','promote_round24.py','write_round24_readme.py','check_call_closure.py','unified-main-corpus-round24.json']:
 rel='work/parallel-main-integration/'+name;cp(ROOT/rel,Path('inputs')/rel)
 if rel.endswith('.py'):support[rel]=sha(ROOT/rel)
for log in (W/'round24-final-unified/suites').rglob('*.log'):
 cp(log,Path('validation-logs')/log.relative_to(W/'round24-final-unified/suites'))
if (W/'round24-initial-queue-failure.json').exists():cp(W/'round24-initial-queue-failure.json','initial-queue-failure.json')
cp(ROOT/'work/parallel-main-data-frontier/round24-source-path-fidelity.json','source-path-fidelity.json')
rel='work/parallel-main-data-frontier/audit_source_paths.py';cp(ROOT/rel,Path('inputs')/rel);support[rel]=sha(ROOT/rel)
for directory in ['work/parallel-main-v3-quote-validation-order','work/parallel-main-v3-quote-fee-tail','work/parallel-main-v3-quote-scanner','work/parallel-main-sweep-recipient-reuse','work/parallel-main-fee-math-module']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for directory,names in [('work/parallel-main-migration-burn',['NATIVE-TRANSFER-REVIEW.json']),('work/parallel-main-v3-quote-fee-tail',['FINAL-RESULT.json','INCREMENTAL-CLI-MANIFEST.json']),('work/parallel-main-v3-quote-scanner',['PARSER-CLI-MANIFEST.json']),('work/parallel-main-sweep-recipient-reuse',['summary.json']),('work/parallel-main-fee-math-module',['summary.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
cp(ROOT/'work/parallel-main-data-frontier/round24-frontier.json','remaining-body-and-data-triage.json')
rel='work/parallel-main-data-frontier/analyze.py';cp(ROOT/rel,Path('inputs')/rel);support[rel]=sha(ROOT/rel)
cp(ROOT/'work/parallel-main-data-frontier/round24-location-objects.json','location-object-triage.json')
rel='work/parallel-main-data-frontier/audit_location_objects.py';cp(ROOT/rel,Path('inputs')/rel);support[rel]=sha(ROOT/rel)
for directory in ['work/parallel-main-quote-token-helper','work/parallel-main-quote-transfer-wrappers','work/parallel-main-create-mayhem-interface','work/parallel-main-optional-sharing']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for directory,names in [('work/parallel-main-quote-token-helper',['summary.json']),('work/parallel-main-quote-transfer-wrappers',['RESULT03.json']),('work/parallel-main-create-mayhem-interface',['CREATION-CPI-REVIEW.json','OUTER-CALLER-REVIEW.json','PLAN01.json','CALLER-ACCOUNT-ORDER.json']),('work/parallel-main-optional-sharing',['DUPLICATES.json','BEFORE-EVENTS.json','ORIGINAL-CALLERS.json','REPORT.json','CLI-MANIFEST.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
cp(W/'round24-initial-superseded.json','superseded-initial.json')
cp(W/'round24-initial-check-state.json','superseded-initial-state.json')
for directory in ['work/parallel-main-legacy-creator-rent','work/parallel-main-v2-creator-vault-rent']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for directory,names in [('work/parallel-main-legacy-creator-rent',['RESULT02.json','INCREMENTAL-CLI-MANIFEST.json','CPI-EVIDENCE.json','STATIC-EVIDENCE.json']),('work/parallel-main-v2-creator-vault-rent',['DELIVERY.json','FINAL-RESULT.json','CLI-MANIFEST.json','DUPLICATES.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
cp(W/'round24-metadata-guard-unified.log','metadata-guard-failure.log')
cp(W/'round24-metadata-guard-check-state.json','metadata-guard-state.json')
cp(W/'round24-pre-finalized-metadata-corpus.json','metadata-guard-corpus.json')
for file in (ROOT/'work/parallel-main-window-boundary-audit').iterdir():
 if file.is_file() and file.suffix in ['.json','.md','.py']:
  cp(file,Path('window-boundary-audit')/file.name)
for file in (ROOT/'work/parallel-main-instruction-coverage').iterdir():
 if file.is_file() and (file.suffix in ['.json','.md','.csv','.py'] or file.name.endswith('.json.gz')):
  cp(file,Path('instruction-coverage')/file.name)
checkpoint['supporting_python_sha256']=support
(P/'CHECKPOINT.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
print(P);print({k:checkpoint[k]for k in ['normalized_windows','raw_windows','matched_text_bytes','full_cases','additional_cases']})
