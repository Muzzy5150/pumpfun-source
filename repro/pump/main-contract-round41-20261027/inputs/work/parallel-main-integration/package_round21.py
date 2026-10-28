"""Seal the verified Round21 main-Pump source, builds and bounded runtime evidence."""
from pathlib import Path
import gzip,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;P=ROOT/'repro/pump/main-contract-round21-20261027';P.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def cp(src,dst):
 out=P/dst;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,out)
full=read(W/'round21-captured-full.json.gz');extra=read(W/'round21-captured-additional.json.gz');build=read(W/'build-round21/build-comparison.json');inv=read(W/'build-round21/normalized-inventory.json');closure=read(W/'round21-closed-call-body-inventory.json');promotion=read(W/'round21-promotion.json')
assert full['case_count']==10468 and len(full['suites'])==44 and not full['mismatches'];assert extra['case_count']==5498 and extra['suite_count']==99 and not extra['diagnostics']['mismatches'];assert full['candidate_sha256']==extra['candidate_sha256']==build['comparison']['candidate_sha256']==promotion['candidate_sha256']
source={};primary={}
for mapping,base,dest,out in [(build['source_sha256'],W/'build-round21/source','source',source),(build['primary_source_sha256'],W/'round21-source/programs/pump','primary',primary)]:
 for name,digest in mapping.items():
  p=ROOT/name;rel=p.relative_to(base);assert sha(p)==digest;cp(p,Path(dest)/rel);out[str(rel)]=digest
for src,dst in [('build-round21/candidate.so','candidate.so'),('build-round21/unstripped.so','unstripped.so'),('build-round21/build-comparison.json','build.json'),('build-round21-repeat/build-comparison.json','repeat-build.json'),('round21-captured-full.json.gz','full.json.gz'),('round21-captured-additional.json.gz','additional.json.gz'),('round21-closed-call-body-inventory.json','closed-calls.json'),('round21-promotion.json','promotion.json'),('round21-integration-plan.json','integration-plan.json')]:cp(W/src,dst)
cp(ROOT/'evidence/original/pump/capture.json','target-capture.json');(P/'inventory.json.gz').write_bytes(gzip.compress((W/'build-round21/normalized-inventory.json').read_bytes(),mtime=0))
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
matched=sum(x['bytes']for x in inv['windows']if x['normalized_matches']);checkpoint={'scope':__doc__,'goal_complete':False,'whole_elf_equal':False,'candidate_sha256':sha(P/'candidate.so'),'unstripped_sha256':sha(P/'unstripped.so'),'original_sha256':build['comparison']['original_sha256'],'source_sha256':source,'primary_source_sha256':primary,'input_python_sha256':py,'loader_receipts':loaders,'full_cases':10468,'full_suites':44,'full_log_cases':full['diagnostics']['log_bearing_cases'],'additional_cases':5498,'additional_suites':99,'additional_log_cases':extra['diagnostics']['log_bearing_cases'],'normalized_windows':inv['counts']['normalized'],'raw_windows':inv['counts']['raw'],'original_windows':len(inv['windows']),'matched_text_bytes':matched,'original_text_bytes':1792208,'closed_call_windows_without_data':closure['counts']['closed_call_graph_windows_without_data_references'],'archived_recipe_reproduced':False,'known_incomplete':'Full ELF, data/relocations, all remaining bodies and newly discovered quote-token owner/helper follow-ups remain unresolved.'};(P/'CHECKPOINT.json').write_text(json.dumps(checkpoint,indent=2)+'\n')

for name in ['verify.py','reproduce.py']:
 cp(ROOT/'repro/pump/main-contract-round20-20261027'/name,name)
for directory in ['work/parallel-main-v2-helpers','work/parallel-main-v3-helpers','work/parallel-main-option-bool','work/parallel-main-v2-handlers','work/parallel-main-v2-context','work/parallel-main-legacy-sell-rent']:
 for f in (ROOT/directory).glob('*.py'):
  cp(f,Path('inputs')/f.relative_to(ROOT))

old_checkpoint=read(ROOT/'repro/pump/main-contract-round20-20261027/CHECKPOINT.json')
support={}
for name in old_checkpoint.get('supporting_python_sha256',{}):
 p=ROOT/name;cp(p,Path('inputs')/name);support[name]=sha(p)
for directory in ['work/parallel-main-fee-market-cap','work/parallel-main-sweep-prepare','work/parallel-main-sweep-quote-predicate','work/parallel-main-decode-envelope','work/parallel-main-admin-cto-rent','work/parallel-main-migrate-prepare','work/parallel-main-migrate-v2-prepare','work/parallel-main-fee-recipient-helper','work/parallel-main-global-fee-waiver','work/parallel-main-fee-waiver','work/parallel-main-sell-v2-buyback','work/parallel-main-buy-v2-order','work/parallel-main-v3-fee-waiver','work/parallel-main-v3-post-ceil','work/parallel-main-v3-validity','work/parallel-main-v3-net-budget','work/parallel-main-create-frontier','work/parallel-main-create-handlers','work/parallel-main-v3-sell-supply','work/parallel-main-create-sizing','work/parallel-main-shared-sell-transfer','work/parallel-main-buy-native-recipient','work/parallel-main-v3-fee-wrapper']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for src,dst in [('round20-integration-plan.json','integration-base-plan.json'),('round21-check-state.json','validation-state.json')]:cp(W/src,dst)
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
verifier=P/'verify.py'
v=verifier.read_text()
needle=' from solders.transaction import VersionedTransaction'
extra=''' proof=read(P/'new-cache-provenance/DIRECT-TRAIT-PARITY.json')
 build_record=read(P/'build.json')
 assert proof['status']=='passed' and build_record['dependency_cache']['key']==proof['cache_key']
 assert sha(P/'dependency-cache-manifest.json')==proof['manifest_sha256']==build_record['dependency_cache']['manifest_sha256']
 for filename,values in proof['elf_hashes'].items():
  assert values['clean']==values['cached']
  for label in ['clean','cached']:assert sha(P/'new-cache-provenance'/label/filename)==values[label]
 for label in ['clean','cached']:
  record=read(P/'new-cache-provenance'/label/'build-comparison.json');assert record['returncode']==0 and record['source_unchanged']
'''
assert v.count(needle)==1;verifier.write_text(v.replace(needle,extra+needle))
for name in ['round21-interrupted-state.json','round21-captured-full.json.gz.failed.json','round21-captured-additional.json.gz.failed.json','round21-resume-proof.json','round21-resumed-full.json.gz.failed.json','round21-resume2-script-bindings.json']:
 cp(W/name,Path('verification-recovery')/name)
for family in ['full','additional']:
 prior=read(W/f'round21-captured-{family}.json.gz.failed.json')
 for name in prior['completed_suites']:
  for suffix in ['.json.gz','.loader.json','.log']:
   cp(W/f'round21-captured-{family}.json.gz.suites'/(name+suffix),Path('verification-recovery')/'retained'/family/(name+suffix))
for name in ['run_round21_full.py','resume_round21.py','resume_round21_tail.py','validate_full_resumed21_tail.py','validate_full_resumed21.py','validate_additional_resumed21.py','finish_round21.py','package_round21.py','promote_round21.py','write_round21_readme.py','check_call_closure.py']:
 rel='work/parallel-main-integration/'+name;cp(ROOT/rel,Path('inputs')/rel);support[rel]=sha(ROOT/rel)
checkpoint['supporting_python_sha256']=support
(P/'CHECKPOINT.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
print(P);print({k:checkpoint[k]for k in ['normalized_windows','raw_windows','matched_text_bytes','full_cases','additional_cases']})
