"""Seal the verified Round33 main-Pump source, builds and bounded runtime evidence."""
from pathlib import Path
import gzip,hashlib,json,shutil
PROFILE_AUDIT_SOURCE = r'''def profile_digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def resolve_profile_entry(inventory,name):
 import posixpath
 for _ in range(64):
  parts=name.split('/')
  for index in range(1,len(parts)+1):
   prefix='/'.join(parts[:index]);entry=inventory.get(prefix,{})
   if 'symlink' in entry:
    name=posixpath.normpath(posixpath.join(posixpath.dirname(prefix),entry['symlink'],*parts[index:]))
    assert name!='..' and not name.startswith(('../','/')),'Escaping SDK cache dependency'
    break
  else:
   return inventory[name]
 raise AssertionError('Cyclic SDK symlink')
def verify_primary_binding(record,expected):
 actual=record['primary_source_sha256']
 assert len(actual)==len(expected),'Primary source file count differs'
 for relative,digest in expected.items():
  matches=[v for k,v in actual.items() if k==relative or k.endswith('/'+relative)]
  assert matches==[digest],('Primary source binding differs',relative)
def verify_profile_record(record,manifest,manifest_sha256,spec,context,implementation_sha256):
 import posixpath
 assert record['returncode']==0 and record['source_unchanged'] is True
 profile=record['target_library_profile']
 assert profile['status']=='verified' and profile['native_host_files_unchanged'] is True
 assert profile['name']==spec['name']==context['name']=='linux-v1.44-sbf'
 assert profile['cache_context']==context
 assert profile['profile_spec_sha256']==context['profile_spec_sha256']
 assert profile['implementation_sha256']==implementation_sha256
 assert profile['file_manifest_sha256']==manifest_sha256
 assert context['target']==spec['target']=='sbf-solana-solana'
 assert context['target_libraries']==spec['target_libraries'] and len(spec['target_libraries'])==25
 assert context['empty_directories']==spec['empty_directories']==['self-contained']
 assert set(manifest)=={'native','prepared'}
 native,prepared=manifest['native'],manifest['prepared']
 assert profile_digest(native)==context['native_sdk_manifest_sha256']
 assert profile_digest(prepared)==context['prepared_sdk_manifest_sha256']
 prefix='rust/lib/rustlib/sbf-solana-solana/lib/'
 for inventory in [native,prepared]:
  for name,value in inventory.items():
   assert name and not name.startswith('/') and posixpath.normpath(name)==name and '..' not in name.split('/')
   if 'symlink' in value:
    assert set(value)=={'symlink'} and not value['symlink'].startswith('/')
    resolved=posixpath.normpath(posixpath.join(posixpath.dirname(name),value['symlink']))
    assert resolved!='..' and not resolved.startswith('../'),'Escaping SDK symlink'
   else:
    assert set(value)=={'sha256','mode'} and len(value['sha256'])==64 and 0<=value['mode']<=0o777
 changed=sorted(name for name in native.keys()|prepared.keys() if native.get(name)!=prepared.get(name))
 assert changed and changed==profile['changed_paths']
 assert all(name.startswith(prefix) for name in changed),'Host/compiler file changed'
 assert {k:v for k,v in native.items() if not k.startswith(prefix)}=={k:v for k,v in prepared.items() if not k.startswith(prefix)}
 actual={name[len(prefix):]:value for name,value in prepared.items() if name.startswith(prefix)}
 assert set(actual)==set(spec['target_libraries']),'Target library inventory differs'
 for name,digest in spec['target_libraries'].items():
  assert '/' not in name and actual[name].get('sha256')==digest and 'symlink' not in actual[name]
 for name,digest in spec['native_tools'].items():
  assert native[name]['sha256']==prepared[name]['sha256']==digest
  assert record['tool_sha256'][Path(name).name]==digest
 sdk=Path(profile['prepared_sdk']);rustc=str(sdk/'rust/bin/rustc')
 assert record['environment']['RUSTC']==rustc
 assert profile['compiler_queries']==[
  {'command':[rustc,'--print','sysroot'],'stdout':str(sdk/'rust')},
  {'command':[rustc,'--print','target-libdir','--target','sbf-solana-solana'],'stdout':str(sdk/prefix.rstrip('/'))}]
 assert record['dependency_cache']['main_freshly_compiled'] is True
 return prepared

def verify_cache_producer_transition(cache_manifest,final,manifest_sha256):
 snapshot=cache_manifest['producer_build_report_snapshot']
 assert cache_manifest['producer_snapshot_sha256']==profile_digest(snapshot)
 added={'main_freshly_compiled','external_fresh','external_rebuilt','published_files','manifest_sha256'}
 before,after=snapshot['dependency_cache'],final['dependency_cache']
 assert set(after)-set(before)==added and set(before)<=set(after),'Unexpected cache.finish transition'
 assert after['main_freshly_compiled'] is True and after['external_fresh']==0 and after['external_rebuilt']>0
 assert after['published_files']==len(cache_manifest['files']) and after['manifest_sha256']==manifest_sha256
 stripped=json.loads(json.dumps(final))
 for name in added:del stripped['dependency_cache'][name]
 assert stripped==snapshot,'Producer inputs or outputs changed after the cache snapshot'

def verify_hybrid_profile(cp):
 spec_file=P/'inputs/scripts/pump_linux_v144_sbf_libraries.json'
 spec=read(spec_file);context=cp['target_library_profile_context']
 implementation_sha256=sha(P/'inputs/scripts/pump_target_library_profile.py')
 assert sha(spec_file)==context['profile_spec_sha256']==cp['additional_input_sha256']['scripts/pump_linux_v144_sbf_libraries.json']
 assert implementation_sha256==cp['input_python_sha256']['scripts/pump_target_library_profile.py']
 assert cp['target_library_profile']==spec['name']=='linux-v1.44-sbf'
 assert cp['target_libraries_bundled'] is False and not list(P.rglob('*.rlib'))
 expected={'build.json','repeat-build.json','canonical-build.json','reproduced-build.json'}
 assert set(cp['target_library_profile_manifests'])==expected
 cache_manifest=read(P/'dependency-cache-manifest.json');proof=read(P/'new-cache-provenance/DIRECT-TRAIT-PARITY.json')
 assert cache_manifest['key']==profile_digest(cache_manifest['context'])==proof['cache_key']==cp['hybrid_cache_key']
 assert proof['profile_context']==cache_manifest['context']['target_library_profile']==context
 assert proof['fresh_main'] is True and proof['main_cache_files']==0 and proof['cache_files']==len(cache_manifest['files'])
 assert proof['default_native_elf_parity'] is True and proof['default_native_key_unchanged']!=proof['cache_key']
 unavailable=proof['producer_target_unavailable_control']
 assert unavailable['status']=='passed' and unavailable['producer_target_absent_before_consumers'] is True and unavailable['consumers_finished_while_producer_target_absent'] is True
 prepared=None;targets=set();sdks=set()
 for name,manifest_name in cp['target_library_profile_manifests'].items():
  record=read(P/name);file=P/manifest_name
  prepared=verify_profile_record(record,read(file),sha(file),spec,context,implementation_sha256)
  verify_primary_binding(record,cp['primary_source_sha256'])
  assert record['dependency_cache']['key']==cp['hybrid_cache_key']
  assert record['dependency_cache']['manifest_sha256']==proof['manifest_sha256']
  assert record['dependency_cache']['status']=='hit'
  targets.add(record['environment']['CARGO_TARGET_DIR']);sdks.add(record['target_library_profile']['prepared_sdk'])
 assert len(targets)==len(sdks)==4,'Four builds must use distinct fresh targets and profile SDKs'
 for name,digest in cache_manifest['context']['sdk'].items():
  assert resolve_profile_entry(prepared,name)['sha256']==digest,('Cache SDK mismatch',name)
 for name in cache_manifest['files']:
  parts=Path(name).parts
  assert not any(part in ['.fingerprint','build','incremental'] for part in parts)
  assert not any(Path(name).name.startswith(prefix) for prefix in ['pump_recovered-','libpump_recovered-','pump-recovered-'])
 for label,proof_field in [('clean','clean_build_report_sha256'),('cached','cached_build_report_sha256')]:
  directory=P/'new-cache-provenance'/label;record=read(directory/'build-comparison.json');file=directory/'target-library-profile-files.json'
  assert sha(directory/'build-comparison.json')==proof[proof_field]
  verify_profile_record(record,read(file),sha(file),spec,context,implementation_sha256)
  assert record['dependency_cache']['key']==cp['hybrid_cache_key']
 verify_cache_producer_transition(cache_manifest,read(P/'new-cache-provenance/clean/build-comparison.json'),sha(P/'dependency-cache-manifest.json'))
 baseline=read(P/'layout-proof/baseline-build.json');file=P/'layout-proof/baseline-target-library-profile-files.json'
 verify_profile_record(baseline,read(file),sha(file),spec,context,implementation_sha256)
 verify_primary_binding(baseline,cp['primary_source_sha256'])
 assert baseline['unstripped_sha256']==sha(P/'layout-proof/baseline.so')
 historical=read(P/'historical-native-provenance/DIRECT-TRAIT-PARITY.json')
 assert historical['cache_key']==proof['default_native_key_unchanged']
 assert historical['cache_key']!=cp['hybrid_cache_key']
 corpus=read(P/'inputs/work/parallel-main-integration/unified-main-corpus-round33.json')
 assert corpus['counts']=={'full':10468,'additional':7283}
 for group,total,count in [('full',10468,44),('additional',7283,148)]:
  rows=[row for row in corpus['suites'] if row['group']==group]
  assert len(rows)==count and sum(row['cases'] for row in rows)==total
 assert cp['full_suites']==44 and cp['additional_suites']==148 and cp['full_cases']+cp['additional_cases']==17751
'''
REPRODUCER_SOURCE = r'''#!/usr/bin/env python3
"""Rebuild the archived main-Pump source with explicit external SBF target libraries."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
ROOT=next(p for p in P.parents if (p/'evidence/original/pump/deployed.so').is_file())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--registry-home',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True)
 p.add_argument('--dependency-cache',type=Path)
 p.add_argument('--sdk',type=Path,help='Native macOS v1.44 SDK; its tool hashes must match the pinned profile.')
 p.add_argument('--target-library-directory',type=Path,required=True,help='External official Linux v1.44 SBF library directory (25 libraries and empty self-contained/).')
 a=p.parse_args();cp=json.loads((P/'CHECKPOINT.json').read_text())
 for name,digest in cp['primary_source_sha256'].items():assert sha(P/'primary'/name)==digest
 for name in ['scripts/pump_build_verified.py','scripts/pump_dependency_cache.py','scripts/pump_target_library_profile.py','scripts/pump_physical_source_wrapper.py']:
  assert sha(P/'inputs'/name)==cp['input_python_sha256'][name]
 assert sha(P/'inputs/scripts/pump_linux_v144_sbf_libraries.json')==cp['additional_input_sha256']['scripts/pump_linux_v144_sbf_libraries.json']
 assert sha(ROOT/'scripts/pump_physical_source_wrapper.py')==cp['input_python_sha256']['scripts/pump_physical_source_wrapper.py']
 sys.path.insert(0,str(P/'inputs/scripts'));path=P/'inputs/scripts/pump_build_verified.py'
 spec=importlib.util.spec_from_file_location('archived_pump_builder',path);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);b.ROOT=ROOT
 sys.argv=[str(path),'--source-directory',str(P/'primary'),'--workspace-layout','--registry-home',str(a.registry_home.resolve()),'--output',str(a.output.resolve()),'--target-library-profile',cp['target_library_profile'],'--target-library-directory',str(a.target_library_directory.resolve())]
 if a.sdk:sys.argv+=['--sdk',str(a.sdk.resolve())]
 if a.dependency_cache:sys.argv+=['--dependency-cache',str(a.dependency_cache.resolve())]
 if cp.get('text_section_order'):
  order=P/cp['text_section_order'];assert sha(order)==cp['text_section_order_sha256'];sys.argv+=['--text-section-order',str(order)]
 b.main();report=json.loads((a.output/'build-comparison.json').read_text())
 assert report['target_library_profile']['cache_context']==cp['target_library_profile_context']
 assert report['target_library_profile']['native_host_files_unchanged'] is True
 assert report['comparison']['candidate_sha256']==cp['candidate_sha256'] and report['unstripped_sha256']==cp['unstripped_sha256']
 print('Archived primary source reproduced both ELF hashes under the pinned hybrid target-library profile.')
if __name__=='__main__':main()
'''
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;P=ROOT/'repro/pump/main-contract-round33-20261027';P.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def cp(src,dst):
 out=P/dst;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,out)
CFG=read(W/'round33-build-config.json')
assert CFG['target_library_profile']=='linux-v1.44-sbf'
corpus=read(W/'unified-main-corpus-round33.json')
assert corpus['counts']=={'full':10468,'additional':7283}
for group,count,suites in [('full',10468,44),('additional',7283,148)]:
 rows=[r for r in corpus['suites'] if r['group']==group]
 assert len(rows)==suites and sum(r['cases'] for r in rows)==count,(group,len(rows))
assert sum(corpus['counts'].values())==17751
full=read(W/'round33-captured-full.json.gz');extra=read(W/'round33-captured-additional.json.gz');build=read(W/'build-round33/build-comparison.json');inv=read(W/'build-round33/normalized-inventory.json');closure=read(W/'round33-closed-call-body-inventory.json');promotion=read(W/'round33-promotion.json')
assert full['case_count']==10468 and len(full['suites'])==44 and not full['mismatches'];assert extra['case_count']==7283 and extra['suite_count']==148 and not extra['diagnostics']['mismatches'];assert full['candidate_sha256']==extra['candidate_sha256']==build['comparison']['candidate_sha256']==promotion['candidate_sha256']
source={};primary={}
for mapping,base,dest,out in [(build['source_sha256'],W/'build-round33/source','source',source),(build['primary_source_sha256'],W/'round33-source/programs/pump','primary',primary)]:
 for name,digest in mapping.items():
  p=ROOT/name;rel=p.relative_to(base);assert sha(p)==digest;cp(p,Path(dest)/rel);out[str(rel)]=digest
for src,dst in [('build-round33/candidate.so','candidate.so'),('build-round33/unstripped.so','unstripped.so'),('build-round33/build-comparison.json','build.json'),('build-round33-repeat/build-comparison.json','repeat-build.json'),('round33-captured-full.json.gz','full.json.gz'),('round33-captured-additional.json.gz','additional.json.gz'),('round33-closed-call-body-inventory.json','closed-calls.json'),('round33-promotion.json','promotion.json'),('round33-integration-plan.json','integration-plan.json')]:cp(W/src,dst)
cp(ROOT/'evidence/original/pump/capture.json','target-capture.json');(P/'inventory.json.gz').write_bytes(gzip.compress((W/'build-round33/normalized-inventory.json').read_bytes(),mtime=0))
inputs={**full['bound_files_sha256'],**{str(ROOT/k):v for k,v in full['script_sha256'].items()},**extra['input_sha256']}
for name in ['scripts/pump_compare_function_bytes.py','scripts/pump_quote_control_function_match.py','scripts/pump_diagnostic_audit.py','scripts/pump_build_verified.py','scripts/pump_dependency_cache.py','scripts/pump_target_library_profile.py','scripts/pump_physical_source_wrapper.py','scripts/build_source_manifest.py','scripts/compare.py','scripts/pump_captured_loader.py','scripts/pump_with_captured_loader.py']:
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
matched=sum(x['bytes']for x in inv['windows']if x['normalized_matches']);checkpoint={'scope':__doc__,'goal_complete':False,'whole_elf_equal':False,'candidate_sha256':sha(P/'candidate.so'),'unstripped_sha256':sha(P/'unstripped.so'),'original_sha256':build['comparison']['original_sha256'],'source_sha256':source,'primary_source_sha256':primary,'input_python_sha256':py,'loader_receipts':loaders,'full_cases':10468,'full_suites':44,'full_log_cases':full['diagnostics']['log_bearing_cases'],'additional_cases':7283,'additional_suites':148,'additional_log_cases':extra['diagnostics']['log_bearing_cases'],'normalized_windows':inv['counts']['normalized'],'raw_windows':inv['counts']['raw'],'original_windows':len(inv['windows']),'matched_text_bytes':matched,'original_text_bytes':1792208,'closed_call_windows_without_data':closure['counts']['closed_call_graph_windows_without_data_references'],'archived_recipe_reproduced':False,'known_incomplete':'Full ELF, data/relocations, remaining bodies and source/build provenance remain unresolved. Observed legacy/V2/Sweep/AdminCto rent differences are corrected in the bounded corpus; full behavior coverage remains unproven.'};(P/'CHECKPOINT.json').write_text(json.dumps(checkpoint,indent=2)+'\n')

for name in ['verify.py','reproduce.py']:
 cp(ROOT/'repro/pump/main-contract-round31-20261027'/name,name)
for directory in ['work/parallel-main-v2-helpers','work/parallel-main-v3-helpers','work/parallel-main-option-bool','work/parallel-main-v2-handlers','work/parallel-main-v2-context','work/parallel-main-legacy-sell-rent']:
 for f in (ROOT/directory).glob('*.py'):
  cp(f,Path('inputs')/f.relative_to(ROOT))

old_checkpoint=read(ROOT/'repro/pump/main-contract-round32-20261027/CHECKPOINT.json')
support={}
for name in old_checkpoint.get('supporting_python_sha256',{}):
 p=ROOT/name;cp(p,Path('inputs')/name);support[name]=sha(p)
for directory in ['work/parallel-main-fee-market-cap','work/parallel-main-sweep-prepare','work/parallel-main-sweep-quote-predicate','work/parallel-main-decode-envelope','work/parallel-main-admin-cto-rent','work/parallel-main-migrate-prepare','work/parallel-main-migrate-v2-prepare','work/parallel-main-fee-recipient-helper','work/parallel-main-global-fee-waiver','work/parallel-main-fee-waiver','work/parallel-main-sell-v2-buyback','work/parallel-main-buy-v2-order','work/parallel-main-v3-fee-waiver','work/parallel-main-v3-post-ceil','work/parallel-main-v3-validity','work/parallel-main-v3-net-budget','work/parallel-main-create-frontier','work/parallel-main-create-handlers','work/parallel-main-v3-sell-supply','work/parallel-main-create-sizing','work/parallel-main-shared-sell-transfer','work/parallel-main-buy-native-recipient','work/parallel-main-v3-fee-wrapper','work/parallel-main-migration-burn','work/parallel-main-buyback-split','work/parallel-main-legacy-buyback-split','work/parallel-main-sell-v2-buyback-accounting','work/parallel-main-v3-buyback-assert','work/parallel-main-v3-cost-order','work/parallel-main-v3-accounting-boundary']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for src,dst in [('round32-integration-plan.json','integration-base-plan.json'),('round33-check-state.json','validation-state.json')]:cp(W/src,dst)
for directory,names in [('work/parallel-main-create-frontier',['OPTION-BOOL-REVIEW.json','OUTLINED-ANCESTOR-DELIVERY.json','STATIC-METADATA-REVIEW.json']),('work/parallel-main-create-handlers',['METADATA-API-REVIEW.json','DATA-FIRST-REVIEW.json']),('work/parallel-main-buy-v2-order',['ATA-ORDER-EVIDENCE.json','summary.json','NEW-CASES.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for directory,names in [('work/parallel-main-create-handlers',['V2-METADATA-COMBINED-REVIEW.json','V2-METADATA-INIT-REVIEW.json','V2-METADATA-AUTHORITY-REVIEW.json']),('work/parallel-main-buy-v2-transfer-helper',['EXACT-EVIDENCE.json','summary.json']),('work/parallel-main-v3-sell-supply',['FULL-RESULT.json','FOCUSED-RESULT.json','EVIDENCE-MANIFEST.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
C=ROOT/'work/parallel-main-create-sizing'
for name in ['FINAL-REVIEW.json','DIRECT-TRAIT-PARITY.json','PRODUCER-INDEPENDENT.json','CACHE-ISOLATION.json']:
 cp(C/name,Path('prior-direct-trait-provenance')/name)
cp(Path(CFG['cache_proof']),'new-cache-provenance/DIRECT-TRAIT-PARITY.json')
for label,directory in [('clean',Path(CFG['producer'])),('cached',Path(CFG['consumer']))]:
 for name in ['candidate.so','unstripped.so','build-comparison.json']:
  cp(directory/name,Path('new-cache-provenance')/label/name)
for directory,names in [('work/parallel-main-buy-native-recipient',['summary.json','PANIC-ORDER-EVIDENCE.json','NEW-CASES.json']),('work/parallel-main-shared-sell-transfer',['FINAL-RESULT.json','EVIDENCE-MANIFEST.json']),('work/parallel-main-v3-fee-wrapper',['NEW-PROBE-MANIFEST.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
cp(Path(CFG['producer'])/'build-comparison.json','fully-clean-dependency-baseline.json')
checkpoint['repeat_build_kind']='Fresh main compilation using hash-verified external-only dependencies under the explicit linux-v1.44-sbf hybrid profile; the profile-specific graph was independently rebuilt without cache and reproduced with its distinct verified cache key.'
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
cp(W/'round33-unified/state.json','queue-state.json')
for directory,names in [('work/parallel-main-migration-burn',['BURN-API-REVIEW.json','BURN-IDENTITY-EVIDENCE.json']),('work/parallel-main-legacy-buyback-split',['summary.json','NEW-CASES.json']),('work/parallel-main-sell-v2-buyback-accounting',['summary.json','NEW-CASES.json']),('work/parallel-main-v3-buyback-assert',['FINAL-RESULT02.json','EVIDENCE-MANIFEST02.json']),('work/parallel-main-v3-cost-order',['FOCUSED-RESULT.json','INCREMENTAL-CLI-MANIFEST.json']),('work/parallel-main-data-frontier',['LAYOUT-TRIAL.json','LAYOUT-RESULT.json','LAYOUT-REVIEW.json','SIGNED-LOG-SOURCE-MAPPINGS.json','SOURCE-PATHS.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for name in ['run_round33_full.py','main_corpus_runner_v3.py','finish_round33.py','package_round33.py','promote_round33.py','write_round33_readme.py','check_call_closure.py','unified-main-corpus-round33.json']:
 rel='work/parallel-main-integration/'+name;cp(ROOT/rel,Path('inputs')/rel)
 if rel.endswith('.py'):support[rel]=sha(ROOT/rel)
for log in (W/'round33-unified/suites').rglob('*.log'):
 cp(log,Path('validation-logs')/log.relative_to(W/'round33-unified/suites'))
if (W/'round33-initial-queue-failure.json').exists():cp(W/'round33-initial-queue-failure.json','initial-queue-failure.json')
cp(ROOT/'work/parallel-main-data-frontier/round33-source-path-fidelity.json','source-path-fidelity.json')
rel='work/parallel-main-data-frontier/audit_source_paths.py';cp(ROOT/rel,Path('inputs')/rel);support[rel]=sha(ROOT/rel)
for directory in ['work/parallel-main-v3-quote-validation-order','work/parallel-main-v3-quote-fee-tail','work/parallel-main-v3-quote-scanner','work/parallel-main-sweep-recipient-reuse','work/parallel-main-fee-math-module']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for directory,names in [('work/parallel-main-migration-burn',['NATIVE-TRANSFER-REVIEW.json']),('work/parallel-main-v3-quote-fee-tail',['FINAL-RESULT.json','INCREMENTAL-CLI-MANIFEST.json']),('work/parallel-main-v3-quote-scanner',['PARSER-CLI-MANIFEST.json']),('work/parallel-main-sweep-recipient-reuse',['summary.json']),('work/parallel-main-fee-math-module',['summary.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
cp(ROOT/'work/parallel-main-data-frontier/round33-frontier.json','remaining-body-and-data-triage.json')
rel='work/parallel-main-data-frontier/analyze.py';cp(ROOT/rel,Path('inputs')/rel);support[rel]=sha(ROOT/rel)
cp(ROOT/'work/parallel-main-data-frontier/round33-location-objects.json','location-object-triage.json')
rel='work/parallel-main-data-frontier/audit_location_objects.py';cp(ROOT/rel,Path('inputs')/rel);support[rel]=sha(ROOT/rel)
for directory in ['work/parallel-main-quote-token-helper','work/parallel-main-quote-transfer-wrappers','work/parallel-main-create-mayhem-interface','work/parallel-main-optional-sharing']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for directory,names in [('work/parallel-main-quote-token-helper',['summary.json']),('work/parallel-main-quote-transfer-wrappers',['RESULT03.json']),('work/parallel-main-create-mayhem-interface',['CREATION-CPI-REVIEW.json','OUTER-CALLER-REVIEW.json','PLAN01.json','CALLER-ACCOUNT-ORDER.json']),('work/parallel-main-optional-sharing',['DUPLICATES.json','BEFORE-EVENTS.json','ORIGINAL-CALLERS.json','REPORT.json','CLI-MANIFEST.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for directory in ['work/parallel-main-legacy-creator-rent','work/parallel-main-v2-creator-vault-rent']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for directory,names in [('work/parallel-main-legacy-creator-rent',['RESULT02.json','INCREMENTAL-CLI-MANIFEST.json','CPI-EVIDENCE.json','STATIC-EVIDENCE.json']),('work/parallel-main-v2-creator-vault-rent',['DELIVERY.json','FINAL-RESULT.json','CLI-MANIFEST.json','DUPLICATES.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for directory in ['work/parallel-main-sweep-recipient-rent','work/parallel-main-admin-holder-rent']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for directory,names in [('work/parallel-main-sweep-recipient-rent',['RESULT01.json','EXHAUSTIVE-CALLGRAPH.json','INCREMENTAL-CLI-MANIFEST.json']),('work/parallel-main-admin-holder-rent',['ADMIN-HOLDER-RENT-REVIEW.json','ATTRIBUTION-AND-BEFORE.json','manifest.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for file in (ROOT/'work/parallel-main-window-boundary-audit').iterdir():
 if file.is_file() and file.suffix in ['.json','.md','.py']:
  cp(file,Path('window-boundary-audit')/file.name)
for file in (ROOT/'work/parallel-main-create-extension-validation').glob('*.py'):
 rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)
for name in ['QUOTE-VALIDATOR-REVIEW01.json','focused-manifest.json']:
 cp(ROOT/'work/parallel-main-create-extension-validation'/name,Path('recovery-evidence/creation-quote-validator')/name)
for file in (ROOT/'work/parallel-main-instruction-coverage').iterdir():
 if file.is_file() and (file.suffix in ['.json','.md','.csv','.py'] or file.name.endswith('.json.gz')):
  cp(file,Path('instruction-coverage')/file.name)
for directory in ['work/parallel-main-create-validation-next','work/parallel-main-receipt-verifier']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
cp(ROOT/'evidence/upstream/pump.json','inputs/evidence/upstream/pump.json')
for directory,names in [('work/parallel-main-create-validation-next',['NESTED-VAULT-DIAGNOSTICS-REVIEW.json','focused-manifest.json']),('work/parallel-main-receipt-verifier',['DELIVERY.json','INTEGRITY-CONTROLS.json']),('work/parallel-main-receipt-capture',['VALIDATED-OVERLAY.json','R25-VALIDATION.json','R25-RETENTION.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
retention=read(W/'round33-transaction-retention.json')
assert retention['status']=='passed' and retention['counts']['fully_backed_pairs']==checkpoint['full_cases']+checkpoint['additional_cases']
cp(W/'round33-transaction-retention.json','transaction-retention.json')
checkpoint['fully_serialized_pairs']=retention['counts']['fully_backed_pairs']
checkpoint['serialized_result_objects']=retention['counts']['verified_result_objects']
checkpoint['additional_input_sha256']={'evidence/upstream/pump.json':sha(ROOT/'evidence/upstream/pump.json')}
verifier=P/'verify.py';v=verifier.read_text();mark=' from solders.transaction import VersionedTransaction'
proof_block=""" import importlib.util
 receipt_spec=importlib.util.spec_from_file_location('complete_transaction_receipt_audit',P/'inputs/work/parallel-main-receipt-verifier/receipt_verifier.py')
 receipt_module=importlib.util.module_from_spec(receipt_spec);receipt_spec.loader.exec_module(receipt_module)
 assert sha(P/'inputs/evidence/upstream/pump.json')==cp['additional_input_sha256']['evidence/upstream/pump.json']
 retention=receipt_module.verify_reports(P/'full.json.gz',P/'additional.json.gz',P/'inputs/evidence/upstream/pump.json',root=ROOT,candidate_sha256=cp['candidate_sha256'],expected_total=cp['full_cases']+cp['additional_cases'])
 assert retention['status']=='passed' and retention['counts']['fully_backed_pairs']==cp['fully_serialized_pairs']
 assert retention['counts']['verified_result_objects']==cp['serialized_result_objects']==2*cp['fully_serialized_pairs']
"""
assert mark in v
if 'complete_transaction_receipt_audit' not in v:v=v.replace(mark,proof_block+mark)
verifier.write_text(v)
for file in (ROOT/'work/parallel-main-create-pool-links').glob('*.py'):
 rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)
for name in ['POOL-VAULT-LINKS-REVIEW.json','focused-manifest.json']:
 cp(ROOT/'work/parallel-main-create-pool-links'/name,Path('recovery-evidence/pool-vault-links')/name)
for directory in ['parallel-main-indirect-call-audit','parallel-main-data-layout-proof','parallel-main-data-layout-remaining']:
 folder=ROOT/'work'/directory
 for f in folder.iterdir():
  if f.is_file() and f.suffix in ['.json','.md','.py','.tsv']:
   cp(f,Path('historical-data-audits')/directory/f.name)
for directory in ['work/parallel-main-nested-comparison-audit','work/parallel-main-create-gate-order','work/parallel-main-legacy-cashback-order','work/parallel-main-unobserved-gates']:
 for file in (ROOT/directory).glob('*.py'):
  rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)
for directory,names in [('work/parallel-main-nested-comparison-audit',['COMPARISON-FAMILY-REVIEW.json','focused-manifest.json']),('work/parallel-main-create-gate-order',['CREATE-GATE-ORDER-REVIEW.json','focused-manifest02.json']),('work/parallel-main-legacy-cashback-order',['FINAL-RESULT.json','CLI-MANIFEST.json','ERROR-ORDER-EVIDENCE.json']),('work/parallel-main-pr264-pump',['REVIEW.json','DELTA.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for file in (ROOT/'work/parallel-main-leaf-validation').glob('*.py'):
 rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)
for name in ['MIGRATE-PAUSABLE-REVIEW.json','focused-manifest.json','migrate-pausable-from-round27.patch','PLAN01.json','PLAN02.json','CALLERS.json','original-17c0f0.asm','original-17c3d8.asm','original-fee-wrapper.asm','original-account-size-call.asm']:
 cp(ROOT/'work/parallel-main-leaf-validation'/name,Path('recovery-evidence/migration-pausable')/name)
for name in ['pump_text_layout.py','pump_text_layout_rustc.py','pump_text_layout_linker.py','pump_text_layout_default.ld']:
 rel='scripts/'+name;cp(ROOT/rel,Path('inputs')/rel)
 if name.endswith('.py'):support[rel]=sha(ROOT/rel)
 else:checkpoint['additional_input_sha256'][rel]=sha(ROOT/rel)
cp(W/'round33-layout/ordered.ld','ordered.ld')
checkpoint['text_section_order']='ordered.ld'
checkpoint['text_section_order_sha256']=sha(P/'ordered.ld')
for file in (W/'round33-layout').iterdir():
 if file.is_file():cp(file,Path('layout-proof')/file.name)
for file in ['RESULT.json','MANIFEST.json','README.md','V2-INPUTS.json','r28-translation.json']:
 cp(ROOT/'work/parallel-main-verified-linker-validation'/file,Path('layout-proof/validated-builder')/file)
cp(W/'LINKER-OPTION-ROOT-REVIEW.json','layout-proof/root-review.json')
cp(W/'round29-builder-installation.json','layout-proof/installation.json')
cp(W/'build-round33-identity/unstripped.so','layout-proof/baseline.so')
cp(W/'build-round33-identity/link/link.map','layout-proof/baseline.map')
cp(W/'build-round33/link/link.map','layout-proof/ordered.map')
for name in ['translation.py','mapfile.py']:
 cp(ROOT/'work/parallel-main-verified-linker-validation/layout_tools'/name,Path('layout-proof/tools')/name)
for name in ['FOLLOWUP-REVIEW.json','LATER-HOPS-REVIEW.json','tail-manifest.json','later-hop-manifest.json']:
 cp(ROOT/'work/parallel-main-error-frontier'/name,Path('recovery-evidence/error-frontier')/name)
for file in (ROOT/'work/parallel-main-error-frontier').glob('*.py'):
 rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)
reproducer=P/'reproduce.py';script=reproducer.read_text();needle=' b.main();report='
replacement=" if cp.get('text_section_order'):\n  order=P/cp['text_section_order'];assert sha(order)==cp['text_section_order_sha256'];sys.argv+=['--text-section-order',str(order)]\n b.main();report="
assert needle in script
if "if cp.get('text_section_order')" not in script:reproducer.write_text(script.replace(needle,replacement))
verifier=P/'verify.py';script=verifier.read_text();needle=" sys.path.insert(0,str(P/'inputs/scripts'))"
layout_check=""" import importlib.util
 sys.path.insert(0,str(P/'layout-proof/tools'))
 layout_spec=importlib.util.spec_from_file_location('archived_layout_translation',P/'layout-proof/tools/translation.py')
 layout_module=importlib.util.module_from_spec(layout_spec);layout_spec.loader.exec_module(layout_module)
 assert sha(P/cp['text_section_order'])==cp['text_section_order_sha256']
 layout_actual=layout_module.check(P/'layout-proof/baseline.so',P/'layout-proof/baseline.map',P/'unstripped.so',P/'layout-proof/ordered.map')
 layout_expected=read(P/'layout-proof/translation.json');layout_expected.pop('scope',None)
 assert layout_actual==layout_expected,'Archived allocated-image translation differs'
"""
assert needle in script
if 'archived_layout_translation' not in script:verifier.write_text(script.replace(needle,layout_check+needle))
for directory,names in [('work/parallel-main-transfer-fee-boundary',['RESULT02.json','RESULT04.json','EVIDENCE-MANIFEST02.json','EVIDENCE-MANIFEST04.json','native-pre-fee02.patch','native-fee04-from02.patch','native-fee04-fromR28.patch']),('work/parallel-main-ata-drop',['ATA-FIXED-ARRAY-REVIEW02.json','ata-matching-info-count-from-pausable.patch']),('work/parallel-main-entrypoint-221',['LOCK-DIFF.json','DATA-DELTA.json','TEXT-AND-RELOCATION-DELTA.json','DIRECT-TRAIT-PARITY.json','FINAL-RESULT.json','MANIFEST.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for file in Path(CFG['entrypoint_directory']).glob('*.py'):
 rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)
cp(W/'round33-build-config.json','build-config.json')
cp(W/'round33-lock-audit.json','lock-audit.json')
for directory,names in [('work/parallel-main-shared-ata',['SHARED-ATA-REVIEW01.json','SHARED-ATA-ADDENDUM.json','AUTHORITY-CONTENT-REVIEW.json','SOURCE-PATH-PROOF.json','SOURCE-ORIGINS.json','manifest.json','authority-manifest.json','shared-ata-from-ata02.patch']),('work/parallel-main-user-quote-wrapper',['RESULT02.json','RESULT03.json','README03.md','MANIFEST03.json','user-quote-wrapper02.patch','user-quote-wrapper03-from02.patch','locations02.json','locations03.json','layout.rs','layout.ll'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for directory in ['work/parallel-main-shared-ata','work/parallel-main-user-quote-wrapper']:
 for file in (ROOT/directory).glob('*.py'):
  rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)

# The native R31 cache remains historical evidence, never a current hybrid seed.
old_package=ROOT/'repro/pump/main-contract-round31-20261027'
for name in ['DIRECT-TRAIT-PARITY.json']:
 cp(old_package/'new-cache-provenance'/name,Path('historical-native-provenance')/name)
for name in ['dependency-cache-manifest.json','build-config.json']:
 cp(old_package/name,Path('historical-native-provenance')/name)
profile_context=build['target_library_profile']['cache_context']
proof=read(Path(CFG['cache_proof']))
assert proof['status']=='passed' and proof['profile_context']==profile_context
assert proof['cache_key']==CFG['cache_key']==cache['key']
assert proof['manifest_sha256']==CFG['manifest_sha256']==cache['manifest_sha256']
checkpoint['target_library_profile']=CFG['target_library_profile']
checkpoint['target_library_profile_context']=profile_context
checkpoint['hybrid_cache_key']=CFG['cache_key']
checkpoint['target_libraries_bundled']=False
checkpoint['target_library_profile_manifests']={
 'build.json':'target-library-profiles/cached-files.json',
 'repeat-build.json':'target-library-profiles/repeat-files.json',
 'canonical-build.json':'target-library-profiles/canonical-files.json',
 'reproduced-build.json':'target-library-profiles/reproduced-files.json'}
for name,directory in [('build.json',W/'build-round33'),('repeat-build.json',W/'build-round33-repeat')]:
 record=read(directory/'build-comparison.json');file=directory/'target-library-profile-files.json'
 assert record['target_library_profile']['cache_context']==profile_context
 assert sha(file)==record['target_library_profile']['file_manifest_sha256']
 cp(file,checkpoint['target_library_profile_manifests'][name])
for label,directory in [('clean',Path(CFG['producer'])),('cached',Path(CFG['consumer']))]:
 file=directory/'target-library-profile-files.json';record=read(directory/'build-comparison.json')
 assert sha(file)==record['target_library_profile']['file_manifest_sha256']
 cp(file,Path('new-cache-provenance')/label/file.name)
for source,dest in [('build-comparison.json','baseline-build.json'),('target-library-profile-files.json','baseline-target-library-profile-files.json')]:
 cp(W/'build-round33-identity'/source,Path('layout-proof')/dest)
cp(ROOT/'scripts/pump_linux_v144_sbf_libraries.json','inputs/scripts/pump_linux_v144_sbf_libraries.json')
checkpoint['additional_input_sha256']['scripts/pump_linux_v144_sbf_libraries.json']=sha(ROOT/'scripts/pump_linux_v144_sbf_libraries.json')
for name in ['CONTROLS.json','CLI-CONTROLS.json','INTEGRATION.json','PRODUCER-INDEPENDENCE.json','ARCHIVE-INPUTS.json','SHARED-INPUT-CHECK.json','PROTOTYPE-FROZEN.json']:
 cp(Path(CFG['profile_directory'])/name,Path('profile-provenance')/name)
for directory,names in [
 ('work/parallel-main-user-quote-generic',['RESULT02.json','CLI-MANIFEST.json','SOURCE-MANIFEST02.json','owned-quote02.patch','owned-order-audit02.json','window-gains02.json']),
 ('work/parallel-main-user-quote-recipient',['RESULT01.json','SOURCE-MANIFEST01.json','recipient-quote01.patch','recipient-order-audit01.json','window-gains01.json']),
 ('work/parallel-main-mint-admission-audit',['MINT-ADMISSION-REVIEW.json','CALLER-POLICY-PROOF.json','incremental-manifest.json','incremental-cases.json','DEDUPLICATION.json','pump-mint-exception-from-round31.patch']),
 ('work/parallel-main-multihop-native-edge',['RESULT01.json','CLI-MANIFEST.json','multihop-native01.patch','native-boundary-audit01.json','window-gains01.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
 for file in (ROOT/directory).glob('*.py'):
  rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)
verifier=P/'verify.py';script=verifier.read_text()
assert 'def verify_hybrid_profile' not in script and script.count('def main():')==1
script=script.replace('def main():',PROFILE_AUDIT_SOURCE+'\ndef main():',1)
needle=" original=ROOT/'evidence/original/pump/deployed.so'"
assert script.count(needle)==1
script=script.replace(needle,' verify_hybrid_profile(cp)\n'+needle,1)
verifier.write_text(script)
(P/'reproduce.py').write_text(REPRODUCER_SOURCE)

for name in ['ROUND33-PACKAGING-REVIEW.json','ROUND33-PACKAGING-APPROVED.json']:
 cp(W/name,Path('packaging-review')/name)
# Preserve the exact added migration definitions, receipts and signed dispatch inputs.
for name in ['RESULT02.json','MANIFEST02.json','SOURCE-MANIFEST02.json','CLI-MANIFEST02.json','additional-manifest02.json','MIGRATION-CASE-GROUPS02.json','PRECEDENCE02.json','GROUP-DRIVER-SMOKE02.json','native-call-proof02.json','amount-audit02.json','diagnostics02.json','invocations02.json','migration-payment02-fromR32.patch','migration-payment02-from01.patch']:
 cp(ROOT/'work/parallel-main-migration-payment-fix'/name,Path('recovery-evidence/migration-payment')/name)
for file in (ROOT/'work/parallel-main-migration-payment-fix').glob('*.py'):
 rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)
for name,digest in corpus['definition_sha256'].items():
 if not name.endswith('.py'):
  assert sha(ROOT/name)==digest
  cp(ROOT/name,Path('inputs')/name)
  checkpoint['additional_input_sha256'][name]=digest
checkpoint['supporting_python_sha256']=support
(P/'CHECKPOINT.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
print(P);print({k:checkpoint[k]for k in ['normalized_windows','raw_windows','matched_text_bytes','full_cases','additional_cases']})
