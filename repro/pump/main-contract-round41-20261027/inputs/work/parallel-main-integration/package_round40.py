"""Seal the verified Round40 main-Pump source, builds and bounded runtime evidence."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,shutil
def corpus_expectations(corpus):
 assert set(corpus['counts'])=={'full','additional'},'Unexpected corpus groups'
 expected={group:{} for group in corpus['counts']}
 for row in corpus['suites']:
  group,name,count=row['group'],row['name'],row['cases']
  assert group in expected and isinstance(name,str) and name
  assert isinstance(count,int) and not isinstance(count,bool) and count>0
  assert name not in expected[group],'Duplicate frozen suite'
  assert isinstance(row['script'],str) and row['script'],'Missing frozen suite script'
  expected[group][name]=row
 for group,rows in expected.items():
  assert rows and sum(r['cases']for r in rows.values())==corpus['counts'][group],'Frozen corpus count mismatch'
 return expected

def paired_rows(value):
 if isinstance(value,dict):
  found=int(isinstance(value.get('original'),dict)and isinstance(value.get('candidate'),dict))
  return found+sum(paired_rows(item)for key,item in value.items()if key not in ['original','candidate'])
 if isinstance(value,list):return sum(paired_rows(item)for item in value)
 return 0

def verify_corpus_report(corpus,group,report,script_hashes):
 expected=corpus_expectations(corpus)[group]
 assert isinstance(report['suites'],dict)and set(report['suites'])==set(expected),'Missing or extra reported suites'
 assert report['case_count']==corpus['counts'][group]
 assert report['suite_count']==len(expected)
 saved=report['results'];assert len(saved)==len(expected)
 by_name={r['name']:r for r in saved};assert len(by_name)==len(saved)and set(by_name)==set(expected),'Missing or duplicate execution receipts'
 for name,row in expected.items():
  actual=report['suites'][name];count=paired_rows(actual)
  assert count==row['cases'],('Missing or extra paired rows',group,name,count,row['cases'])
  if 'case_count' in actual:assert actual['case_count']==count
  if isinstance(actual.get('cases'),int):assert actual['cases']==count
  record=by_name[name]
  assert record['group']==group and record['case_count']==count
  assert row['script'] in script_hashes,'Missing authenticated suite script hash'
  expected_hash=script_hashes[row['script']]
  if row['script'] in corpus['definition_sha256']:assert corpus['definition_sha256'][row['script']]==expected_hash
  assert record['script_sha256']==expected_hash
  assert report['script_sha256'][row['script']]==expected_hash
 return sum(row['cases']for row in expected.values())

def corpus_additions(previous,current):
 before=corpus_expectations(previous);after=corpus_expectations(current);rows=[]
 for group,old in before.items():
  assert set(old)<=set(after[group]),'Prior suite missing from frozen corpus'
  for name,row in after[group].items():
   delta=row['cases']-old.get(name,{}).get('cases',0)
   assert delta>=0,('Prior suite lost cases',group,name)
   if delta:rows.append({'group':group,'name':name,'script':row['script'],'new_cases':delta})
 return {'new_cases':sum(r['new_cases']for r in rows),'new_suite_count':sum(name not in before[group]for group in after for name in after[group]),'components':rows}


def normalized_window_delta(previous,current):
 assert previous['original_sha256']==current['original_sha256'],'Original inventory differs'
 before={row['start']for row in previous['windows']if row['normalized_matches']}
 after={row['start']for row in current['windows']if row['normalized_matches']}
 assert not before-after,('Previously matched normalized windows lost',sorted(before-after))
 return {'before':len(before),'after':len(after),'gains':sorted(after-before),'losses':[]}

PROFILE_AUDIT_SOURCE = r'''def normalized_window_delta(previous,current):
 assert previous['original_sha256']==current['original_sha256'],'Original inventory differs'
 before={row['start']for row in previous['windows']if row['normalized_matches']}
 after={row['start']for row in current['windows']if row['normalized_matches']}
 assert not before-after,('Previously matched normalized windows lost',sorted(before-after))
 return {'before':len(before),'after':len(after),'gains':sorted(after-before),'losses':[]}

def corpus_expectations(corpus):
 assert set(corpus['counts'])=={'full','additional'},'Unexpected corpus groups'
 expected={group:{} for group in corpus['counts']}
 for row in corpus['suites']:
  group,name,count=row['group'],row['name'],row['cases']
  assert group in expected and isinstance(name,str) and name
  assert isinstance(count,int) and not isinstance(count,bool) and count>0
  assert name not in expected[group],'Duplicate frozen suite'
  assert isinstance(row['script'],str) and row['script'],'Missing frozen suite script'
  expected[group][name]=row
 for group,rows in expected.items():
  assert rows and sum(r['cases']for r in rows.values())==corpus['counts'][group],'Frozen corpus count mismatch'
 return expected

def paired_rows(value):
 if isinstance(value,dict):
  found=int(isinstance(value.get('original'),dict)and isinstance(value.get('candidate'),dict))
  return found+sum(paired_rows(item)for key,item in value.items()if key not in ['original','candidate'])
 if isinstance(value,list):return sum(paired_rows(item)for item in value)
 return 0

def verify_corpus_report(corpus,group,report,script_hashes):
 expected=corpus_expectations(corpus)[group]
 assert isinstance(report['suites'],dict)and set(report['suites'])==set(expected),'Missing or extra reported suites'
 assert report['case_count']==corpus['counts'][group]
 assert report['suite_count']==len(expected)
 saved=report['results'];assert len(saved)==len(expected)
 by_name={r['name']:r for r in saved};assert len(by_name)==len(saved)and set(by_name)==set(expected),'Missing or duplicate execution receipts'
 for name,row in expected.items():
  actual=report['suites'][name];count=paired_rows(actual)
  assert count==row['cases'],('Missing or extra paired rows',group,name,count,row['cases'])
  if 'case_count' in actual:assert actual['case_count']==count
  if isinstance(actual.get('cases'),int):assert actual['cases']==count
  record=by_name[name]
  assert record['group']==group and record['case_count']==count
  assert row['script'] in script_hashes,'Missing authenticated suite script hash'
  expected_hash=script_hashes[row['script']]
  if row['script'] in corpus['definition_sha256']:assert corpus['definition_sha256'][row['script']]==expected_hash
  assert record['script_sha256']==expected_hash
  assert report['script_sha256'][row['script']]==expected_hash
 return sum(row['cases']for row in expected.values())

def corpus_additions(previous,current):
 before=corpus_expectations(previous);after=corpus_expectations(current);rows=[]
 for group,old in before.items():
  assert set(old)<=set(after[group]),'Prior suite missing from frozen corpus'
  for name,row in after[group].items():
   delta=row['cases']-old.get(name,{}).get('cases',0)
   assert delta>=0,('Prior suite lost cases',group,name)
   if delta:rows.append({'group':group,'name':name,'script':row['script'],'new_cases':delta})
 return {'new_cases':sum(r['new_cases']for r in rows),'new_suite_count':sum(name not in before[group]for group in after for name in after[group]),'components':rows}


def profile_digest(value):
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
def verify_profile_record(record,manifest,manifest_sha256,spec,context,implementation_sha256,require_cached=True):
 import posixpath
 assert record['returncode']==0 and record['source_unchanged'] is True
 profile=record['target_library_profile']
 assert profile['status']=='verified' and profile['native_host_files_unchanged'] is True
 assert profile['name']==spec['name']==context['name']=='linux-v1.44-sbpf'
 assert profile['cache_context']==context
 assert profile['profile_spec_sha256']==context['profile_spec_sha256']
 assert profile['implementation_sha256']==implementation_sha256
 assert profile['file_manifest_sha256']==manifest_sha256
 assert context['target']==spec['target']=='sbpf-solana-solana'
 assert context['target_libraries']==spec['target_libraries'] and len(spec['target_libraries'])==25
 assert context['empty_directories']==spec['empty_directories']==['self-contained']
 assert set(manifest)=={'native','prepared'}
 native,prepared=manifest['native'],manifest['prepared']
 assert profile_digest(native)==context['native_sdk_manifest_sha256']
 assert profile_digest(prepared)==context['prepared_sdk_manifest_sha256']
 prefix='rust/lib/rustlib/sbpf-solana-solana/lib/'
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
  {'command':[rustc,'--print','target-libdir','--target','sbpf-solana-solana'],'stdout':str(sdk/prefix.rstrip('/'))}]
 if require_cached:assert record['dependency_cache']['main_freshly_compiled'] is True
 else:assert 'dependency_cache' not in record,'Cold producer must not inherit compiled artifacts'
 return prepared

def verify_cache_producer_transition(cache_manifest,final,manifest_sha256):
 snapshot=cache_manifest['producer_build_report_snapshot']
 assert cache_manifest['producer_snapshot_sha256']==profile_digest(snapshot)
 if 'dependency_cache' not in snapshot:
  assert 'dependency_cache' not in final and final==snapshot,'No-cache producer changed after import'
  assert final['returncode']==0 and final['source_unchanged'] is True
  return
 added={'main_freshly_compiled','external_fresh','external_rebuilt','published_files','manifest_sha256'}
 before,after=snapshot['dependency_cache'],final['dependency_cache']
 assert set(after)-set(before)==added and set(before)<=set(after),'Unexpected cache.finish transition'
 assert after['main_freshly_compiled'] is True and after['external_fresh']==0 and after['external_rebuilt']>0
 assert after['published_files']==len(cache_manifest['files']) and after['manifest_sha256']==manifest_sha256
 stripped=json.loads(json.dumps(final))
 for name in added:del stripped['dependency_cache'][name]
 assert stripped==snapshot,'Producer inputs or outputs changed after the cache snapshot'

def verify_hybrid_profile(cp):
 spec_file=P/'inputs/scripts/pump_linux_v144_sbpf_libraries.json'
 spec=read(spec_file);context=cp['target_library_profile_context']
 producer_primary=cp['cache_primary_source_sha256']
 for name in ['Cargo.toml','Cargo.lock']:
  assert producer_primary[name]==cp['primary_source_sha256'][name],('Cache/final dependency manifest differs',name)
 for name,digest in producer_primary.items():assert sha(P/'new-cache-provenance/primary'/name)==digest
 implementation_sha256=sha(P/'inputs/scripts/pump_target_library_profile.py')
 assert sha(spec_file)==context['profile_spec_sha256']==cp['additional_input_sha256']['scripts/pump_linux_v144_sbpf_libraries.json']
 assert implementation_sha256==cp['input_python_sha256']['scripts/pump_target_library_profile.py']
 assert cp['target_library_profile']==spec['name']=='linux-v1.44-sbpf'
 assert cp['target_libraries_bundled'] is False and not list(P.rglob('*.rlib'))
 expected={'build.json','repeat-build.json','canonical-build.json','reproduced-build.json'}
 assert set(cp['target_library_profile_manifests'])==expected
 cache_manifest=read(P/'dependency-cache-manifest.json');proof=read(P/'new-cache-provenance/DIRECT-TRAIT-PARITY.json')
 assert cache_manifest['key']==profile_digest(cache_manifest['context'])==proof['cache_key']==cp['hybrid_cache_key']
 assert proof['profile_context']==cache_manifest['context']['target_library_profile']==context
 assert proof['fresh_main'] is True and proof['main_cache_files']==0 and proof['cache_files']==len(cache_manifest['files'])
 # Historical native-cache parity is not a property of this new feature graph.
 unavailable=proof['producer_target_unavailable_control']
 assert unavailable['status']=='passed' and unavailable['producer_target_absent_before_control'] is True and unavailable['consumer_finished_while_producer_target_absent'] is True and unavailable['producer_target_restored'] is True
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
  verify_profile_record(record,read(file),sha(file),spec,context,implementation_sha256,require_cached=label!='clean')
  verify_primary_binding(record,producer_primary)
  assert sha(directory/'candidate.so')==record['comparison']['candidate_sha256'] and sha(directory/'unstripped.so')==record['unstripped_sha256']
  if label!='clean':
   assert record['dependency_cache']['key']==cp['hybrid_cache_key']
   assert record['dependency_cache']['status']=='hit' and record['dependency_cache']['manifest_sha256']==proof['manifest_sha256']
   assert sha(directory/'candidate.so')==sha(P/'new-cache-provenance/clean/candidate.so')
   assert sha(directory/'unstripped.so')==sha(P/'new-cache-provenance/clean/unstripped.so')
 verify_cache_producer_transition(cache_manifest,read(P/'new-cache-provenance/clean/build-comparison.json'),sha(P/'dependency-cache-manifest.json'))
 control_dir=P/'new-cache-provenance/unavailable'
 control=read(control_dir/'build-comparison.json')
 assert sha(control_dir/'build-comparison.json')==unavailable['consumer_report_sha256']
 file=control_dir/'target-library-profile-files.json'
 verify_profile_record(control,read(file),sha(file),spec,context,implementation_sha256)
 verify_primary_binding(control,producer_primary)
 assert control['dependency_cache']['status']=='hit' and control['dependency_cache']['key']==cp['hybrid_cache_key']
 assert control['dependency_cache']['manifest_sha256']==proof['manifest_sha256']
 assert control['comparison']['candidate_sha256']==sha(control_dir/'candidate.so')==sha(P/'new-cache-provenance/clean/candidate.so')
 assert control['unstripped_sha256']==sha(control_dir/'unstripped.so')==sha(P/'new-cache-provenance/clean/unstripped.so')
 baseline=read(P/'layout-proof/baseline-build.json');file=P/'layout-proof/baseline-target-library-profile-files.json'
 verify_profile_record(baseline,read(file),sha(file),spec,context,implementation_sha256)
 verify_primary_binding(baseline,cp['primary_source_sha256'])
 assert baseline['unstripped_sha256']==sha(P/'layout-proof/baseline.so')
 targets.add(baseline['environment']['CARGO_TARGET_DIR']);sdks.add(baseline['target_library_profile']['prepared_sdk'])
 archived_identity=read(P/'archive-reproduction/identity-build.json')
 file=P/'archive-reproduction/identity-target-library-profile-files.json'
 verify_profile_record(archived_identity,read(file),sha(file),spec,context,implementation_sha256)
 verify_primary_binding(archived_identity,cp['primary_source_sha256'])
 assert archived_identity['unstripped_sha256']==sha(P/'archive-reproduction/identity.so')
 assert archived_identity['dependency_cache']['key']==cp['hybrid_cache_key']
 assert archived_identity['dependency_cache']['manifest_sha256']==proof['manifest_sha256']
 targets.add(archived_identity['environment']['CARGO_TARGET_DIR']);sdks.add(archived_identity['target_library_profile']['prepared_sdk'])
 assert len(targets)==len(sdks)==6,'Four final and two identity compilations require distinct targets/profile SDKs'

 historical=read(P/'historical-native-provenance/DIRECT-TRAIT-PARITY.json')
 assert historical['cache_key']!=cp['hybrid_cache_key']
 corpus=read(P/'inputs/work/parallel-main-integration/unified-main-corpus-round40.json')
 assert sha(P/'inputs/work/parallel-main-integration/unified-main-corpus-round40.json')==cp['frozen_corpus_sha256']
 expected=corpus_expectations(corpus)
 for group,rows in expected.items():
  assert cp[group+'_suites']==len(rows) and cp[group+'_cases']==corpus['counts'][group]
  verify_corpus_report(corpus,group,read(P/('full.json.gz'if group=='full'else'additional.json.gz')),{**cp['input_python_sha256'],**cp['supporting_python_sha256']})
 assert corpus_additions(read(P/'corpus/previous-round39.json'),corpus)==cp['case_addition_breakdown']
 assert normalized_window_delta(read(P/'prior-inventory.json.gz'),read(P/'inventory.json.gz'))==cp['normalized_delta_from_previous']

def verify_data_artifacts(cp):
 import importlib.util
 support=P/'archive-support/verify_archive.py'
 assert sha(support)==cp['archive_support_sha256']['verify_archive.py']
 spec=importlib.util.spec_from_file_location('checkpoint_data_archive',support)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 data=cp['data_order'];assert data['status']=='passed'
 assert sha(P/cp['text_section_order'])==cp['text_section_order_sha256']
 assert sha(P/cp['combined_section_order'])==cp['combined_section_order_sha256']
 assert sha(P/cp['identity_text_order'])==cp['identity_text_order_sha256']
 assert set(data['builds'])=={'build.json','repeat-build.json','canonical-build.json','reproduced-build.json'}
 for name,artifacts in data['builds'].items():
  record=read(P/name);certificate=P/artifacts['certificate'];transformation=P/artifacts['transformation']
  assert record['data_order']['status']=='passed'
  assert sha(certificate)==record['data_order']['certificate_sha256']==artifacts['certificate_sha256']
  assert sha(transformation)==record['data_order']['transformation_sha256']==artifacts['transformation_sha256']
  proof=read(transformation);assert proof['status']=='passed' and proof['all_allocated_bytes_checked'] and proof['all_other_file_bytes_checked']
  assert proof['candidate_sha256']==cp['unstripped_sha256']
 for label in ['initial','reproduced']:
  a=data['archive_replays'][label]
  actual=module.verify_archive(original_elf=ROOT/'evidence/original/pump/deployed.so',baseline_elf=P/a['baseline_elf'],baseline_map=P/a['baseline_map'],final_elf=P/'unstripped.so',final_map=P/a['final_map'],admitted_certificate=P/a['certificate'],bindings=P/a['bindings'],bindings_sha256=a['bindings_sha256'],tools_directory=P/'inputs/scripts')
  assert actual['status']=='passed' and actual['fresh_admission'] is False and actual['certificate_paths_rewritten'] is False
  assert actual['transformation']['candidate_sha256']==cp['unstripped_sha256']
  expected=read(P/a['proof']);assert actual['transformation']==expected['transformation']
 assert data['archive_replays']['initial']['certificate_sha256']!=data['archive_replays']['reproduced']['certificate_sha256'],'Archive must derive a fresh certificate'

'''
REPRODUCER_SOURCE = r'''#!/usr/bin/env python3
"""Rebuild archived primary: fresh identity, new certificate, then fresh final ELF."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
ROOT=next(p for p in P.parents if (p/'evidence/original/pump/deployed.so').is_file())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--registry-home',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True,help='Fresh final build directory; identity and certificate use separate sibling paths.')
 p.add_argument('--dependency-cache',type=Path,required=True)
 p.add_argument('--sdk',type=Path)
 p.add_argument('--target-library-directory',type=Path,required=True)
 a=p.parse_args();cp=json.loads((P/'CHECKPOINT.json').read_text())
 final=a.output.resolve();identity=final.with_name(final.name+'-identity');certificate=final.with_name(final.name+'-data-order-certificate.json')
 assert not final.exists() and not identity.exists() and not certificate.exists(),'Use fresh reproduction paths'
 for name,digest in cp['primary_source_sha256'].items():assert sha(P/'primary'/name)==digest
 for name in ['scripts/pump_build_verified.py','scripts/pump_dependency_cache.py','scripts/pump_target_library_profile.py','scripts/pump_physical_source_wrapper.py','scripts/pump_text_layout.py','scripts/pump_data_order.py','scripts/pump_derive_data_order.py']:
  assert sha(P/'inputs'/name)==cp['input_python_sha256'].get(name,cp['supporting_python_sha256'].get(name))
 assert sha(P/'inputs/scripts/pump_linux_v144_sbpf_libraries.json')==cp['additional_input_sha256']['scripts/pump_linux_v144_sbpf_libraries.json']
 assert sha(P/'inputs/scripts/pump_linux_v144_sbf_libraries.json')==cp['additional_input_sha256']['scripts/pump_linux_v144_sbf_libraries.json']
 assert sha(ROOT/'scripts/pump_physical_source_wrapper.py')==cp['input_python_sha256']['scripts/pump_physical_source_wrapper.py']
 pure=P/cp['text_section_order'];identity_script=P/cp['identity_text_order']
 assert sha(pure)==cp['text_section_order_sha256'] and sha(identity_script)==cp['identity_text_order_sha256']
 sys.path.insert(0,str(P/'inputs/scripts'));path=P/'inputs/scripts/pump_build_verified.py'
 spec=importlib.util.spec_from_file_location('archived_pump_builder',path);builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder);builder.ROOT=ROOT
 common=[str(path),'--source-directory',str(P/'primary'),'--workspace-layout','--registry-home',str(a.registry_home.resolve()),'--dependency-cache',str(a.dependency_cache.resolve()),'--target-library-profile',cp['target_library_profile'],'--target-library-directory',str(a.target_library_directory.resolve())]
 if a.sdk:common+=['--sdk',str(a.sdk.resolve())]
 sys.argv=common+['--text-section-order',str(identity_script),'--output',str(identity)];builder.main()
 first=json.loads((identity/'build-comparison.json').read_text())
 assert first['returncode']==0 and first['source_unchanged'] and first['dependency_cache']['main_freshly_compiled']
 import pump_data_order
 sys.argv=[str(P/'inputs/scripts/pump_derive_data_order.py'),'--baseline-build',str(identity),'--text-section-order',str(pure),'--output',str(certificate)]
 pump_data_order.main()
 assert sha(certificate)!=cp['data_order']['archive_replays']['initial']['certificate_sha256'],'Reproduction must derive a fresh certificate'
 sys.argv=common+['--text-section-order',str(pure),'--data-order-certificate',str(certificate),'--output',str(final)];builder.main()
 report=json.loads((final/'build-comparison.json').read_text())
 assert report['target_library_profile']['cache_context']==cp['target_library_profile_context']
 assert report['target_library_profile']['native_host_files_unchanged'] is True
 helper=P/'archive-support/reproduction.py';assert sha(helper)==cp['archive_support_sha256']['reproduction.py']
 spec=importlib.util.spec_from_file_location('archived_final_gate',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 proof=module.verify_final(final,certificate,{'candidate.so':cp['candidate_sha256'],'unstripped.so':cp['unstripped_sha256']})
 result={'status':'passed','identity_build_directory':str(identity),'final_build_directory':str(final),'certificate':str(certificate),'certificate_sha256':sha(certificate),'identity_candidate_sha256':sha(identity/'candidate.so'),'identity_unstripped_sha256':sha(identity/'unstripped.so'),'fresh_certificate':True,'final_proof':proof}
 (final/'archive-reproduction.json').write_text(json.dumps(result,indent=2)+'\n')
 print('Fresh archive identity and final compilations reproduced both expected ELF hashes.')
if __name__=='__main__':main()
'''
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;P=ROOT/'repro/pump/main-contract-round40-20261027';P.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def cp(src,dst):
 out=P/dst;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,out)
CFG=read(W/'round40-build-config.json')
assert CFG['target_library_profile']=='linux-v1.44-sbpf'
corpus=read(W/'unified-main-corpus-round40.json')
expected=corpus_expectations(corpus)
previous_corpus_path=ROOT/'repro/pump/main-contract-round39-20261027/inputs/work/parallel-main-integration/unified-main-corpus-round39.json'
previous_corpus=read(previous_corpus_path)
additions=corpus_additions(previous_corpus,corpus)
integration_plan=read(W/'round40-integration-plan.json')
assert additions['new_cases']==integration_plan['new_cases'],'Frozen manifest/plan additions differ'
# The stronger extension test is retained byte-for-byte as a corpus definition.
assert expected['full']['extension']==corpus_expectations(previous_corpus)['full']['extension']
prior_checkpoint=read(ROOT/'repro/pump/main-contract-round39-20261027/CHECKPOINT.json')
assert expected['full']['extension']['cases']==prior_checkpoint['strengthened_existing_case_definitions']
cp(previous_corpus_path,'corpus/previous-round39.json')
full=read(W/'round40-captured-full.json.gz');extra=read(W/'round40-captured-additional.json.gz');build=read(W/'build-round40/build-comparison.json');inv=read(W/'build-round40/normalized-inventory.json');closure=read(W/'round40-closed-call-body-inventory.json');promotion=read(W/'round40-promotion.json')
prior_inventory_path=ROOT/'repro/pump/main-contract-round39-20261027/inventory.json.gz'
normal_delta=normalized_window_delta(read(prior_inventory_path),inv)
cp(prior_inventory_path,'prior-inventory.json.gz')
script_hashes={row['script']:sha(ROOT/row['script'])for row in corpus['suites']}
verify_corpus_report(corpus,'full',full,script_hashes);verify_corpus_report(corpus,'additional',extra,script_hashes)
assert not full['mismatches'] and not extra['diagnostics']['mismatches'];assert full['candidate_sha256']==extra['candidate_sha256']==build['comparison']['candidate_sha256']==promotion['candidate_sha256']
source={};primary={}
for mapping,base,dest,out in [(build['source_sha256'],W/'build-round40/source','source',source),(build['primary_source_sha256'],Path(build['primary_source_directory']),'primary',primary)]:
 for name,digest in mapping.items():
  p=ROOT/name;rel=p.relative_to(base);assert sha(p)==digest;cp(p,Path(dest)/rel);out[str(rel)]=digest
for name,digest in read(W/'round40-integration-plan.json')['changes'].items():assert primary[name]==digest,('Frozen source change differs',name)
for src,dst in [('build-round40/candidate.so','candidate.so'),('build-round40/unstripped.so','unstripped.so'),('build-round40/build-comparison.json','build.json'),('build-round40-repeat/build-comparison.json','repeat-build.json'),('round40-captured-full.json.gz','full.json.gz'),('round40-captured-additional.json.gz','additional.json.gz'),('round40-closed-call-body-inventory.json','closed-calls.json'),('round40-promotion.json','promotion.json'),('round40-integration-plan.json','integration-plan.json')]:cp(W/src,dst)
cp(ROOT/'evidence/original/pump/capture.json','target-capture.json');(P/'inventory.json.gz').write_bytes(gzip.compress((W/'build-round40/normalized-inventory.json').read_bytes(),mtime=0))
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
matched=sum(x['bytes']for x in inv['windows']if x['normalized_matches']);checkpoint={'scope':__doc__,'goal_complete':False,'whole_elf_equal':False,'candidate_sha256':sha(P/'candidate.so'),'unstripped_sha256':sha(P/'unstripped.so'),'original_sha256':build['comparison']['original_sha256'],'source_sha256':source,'primary_source_sha256':primary,'input_python_sha256':py,'selected_source_changes':read(W/'round40-integration-plan.json')['changes'],'new_distinct_case_definitions':additions['new_cases'],'case_addition_breakdown':additions,'strengthened_existing_case_definitions':prior_checkpoint['strengthened_existing_case_definitions'],'extension_definition_retained_unchanged':True,'frozen_corpus_sha256':sha(W/'unified-main-corpus-round40.json'),'loader_receipts':loaders,'full_cases':corpus['counts']['full'],'full_suites':len(expected['full']),'full_log_cases':full['diagnostics']['log_bearing_cases'],'additional_cases':corpus['counts']['additional'],'additional_suites':len(expected['additional']),'additional_log_cases':extra['diagnostics']['log_bearing_cases'],'normalized_windows':inv['counts']['normalized'],'normalized_delta_from_previous':normal_delta,'raw_windows':inv['counts']['raw'],'original_windows':len(inv['windows']),'matched_text_bytes':matched,'original_text_bytes':1792208,'closed_call_windows_without_data':closure['counts']['closed_call_graph_windows_without_data_references'],'archived_recipe_reproduced':False,'known_incomplete':'Full ELF, data/relocations, remaining bodies and source/build provenance remain unresolved. Observed legacy/V2/Sweep/AdminCto rent differences are corrected in the bounded corpus; full behavior coverage remains unproven.'};checkpoint['diagnostic_scope'] = 'Structured Anchor errors, panic payloads and comparison operands; not universal ordinary success-log equality.'; checkpoint['known_incomplete'] += ' A separate post-freeze ClaimCashbackV2 invalid-quote-program error-precedence and zero-balance log mismatch is queued for the next checkpoint.';(P/'CHECKPOINT.json').write_text(json.dumps(checkpoint,indent=2)+'\n')

for name in ['verify.py','reproduce.py']:
 cp(ROOT/'repro/pump/main-contract-round31-20261027'/name,name)
for directory in ['work/parallel-main-v2-helpers','work/parallel-main-v3-helpers','work/parallel-main-option-bool','work/parallel-main-v2-handlers','work/parallel-main-v2-context','work/parallel-main-legacy-sell-rent']:
 for f in (ROOT/directory).glob('*.py'):
  cp(f,Path('inputs')/f.relative_to(ROOT))

old_checkpoint=read(ROOT/'repro/pump/main-contract-round39-20261027/CHECKPOINT.json')
support={}
for name in old_checkpoint.get('supporting_python_sha256',{}):
 p=ROOT/name;cp(p,Path('inputs')/name);support[name]=sha(p)
for directory in ['work/parallel-main-fee-market-cap','work/parallel-main-sweep-prepare','work/parallel-main-sweep-quote-predicate','work/parallel-main-decode-envelope','work/parallel-main-admin-cto-rent','work/parallel-main-migrate-prepare','work/parallel-main-migrate-v2-prepare','work/parallel-main-fee-recipient-helper','work/parallel-main-global-fee-waiver','work/parallel-main-fee-waiver','work/parallel-main-sell-v2-buyback','work/parallel-main-buy-v2-order','work/parallel-main-v3-fee-waiver','work/parallel-main-v3-post-ceil','work/parallel-main-v3-validity','work/parallel-main-v3-net-budget','work/parallel-main-create-frontier','work/parallel-main-create-handlers','work/parallel-main-v3-sell-supply','work/parallel-main-create-sizing','work/parallel-main-shared-sell-transfer','work/parallel-main-buy-native-recipient','work/parallel-main-v3-fee-wrapper','work/parallel-main-migration-burn','work/parallel-main-buyback-split','work/parallel-main-legacy-buyback-split','work/parallel-main-sell-v2-buyback-accounting','work/parallel-main-v3-buyback-assert','work/parallel-main-v3-cost-order','work/parallel-main-v3-accounting-boundary']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for src,dst in [('round39-integration-plan.json','integration-base-plan.json'),('round40-check-state.json','validation-state.json')]:cp(W/src,dst)
for directory,names in [('work/parallel-main-create-frontier',['OPTION-BOOL-REVIEW.json','OUTLINED-ANCESTOR-DELIVERY.json','STATIC-METADATA-REVIEW.json']),('work/parallel-main-create-handlers',['METADATA-API-REVIEW.json','DATA-FIRST-REVIEW.json']),('work/parallel-main-buy-v2-order',['ATA-ORDER-EVIDENCE.json','summary.json','NEW-CASES.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for directory,names in [('work/parallel-main-create-handlers',['V2-METADATA-COMBINED-REVIEW.json','V2-METADATA-INIT-REVIEW.json','V2-METADATA-AUTHORITY-REVIEW.json']),('work/parallel-main-buy-v2-transfer-helper',['EXACT-EVIDENCE.json','summary.json']),('work/parallel-main-v3-sell-supply',['FULL-RESULT.json','FOCUSED-RESULT.json','EVIDENCE-MANIFEST.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
C=ROOT/'work/parallel-main-create-sizing'
for name in ['FINAL-REVIEW.json','DIRECT-TRAIT-PARITY.json','PRODUCER-INDEPENDENT.json','CACHE-ISOLATION.json']:
 cp(C/name,Path('prior-direct-trait-provenance')/name)
cp(Path(CFG['cache_proof']),'new-cache-provenance/DIRECT-TRAIT-PARITY.json')
independence=read(Path(CFG['cache_proof']))['producer_target_unavailable_control']
control_directory=Path(independence['consumer_directory'])
for name in ['candidate.so','unstripped.so','build-comparison.json','target-library-profile-files.json']:
 cp(control_directory/name,Path('new-cache-provenance/unavailable')/name)
for label,directory in [('clean',Path(CFG['producer'])),('cached',Path(CFG['consumer']))]:
 for name in ['candidate.so','unstripped.so','build-comparison.json']:
  cp(directory/name,Path('new-cache-provenance')/label/name)
for directory,names in [('work/parallel-main-buy-native-recipient',['summary.json','PANIC-ORDER-EVIDENCE.json','NEW-CASES.json']),('work/parallel-main-shared-sell-transfer',['FINAL-RESULT.json','EVIDENCE-MANIFEST.json']),('work/parallel-main-v3-fee-wrapper',['NEW-PROBE-MANIFEST.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
cp(Path(CFG['producer'])/'build-comparison.json','fully-clean-dependency-baseline.json')
producer_record=read(Path(CFG['producer'])/'build-comparison.json')
producer_root=Path(producer_record['primary_source_directory'])
producer_primary={}
for name,digest in producer_record['primary_source_sha256'].items():
 wrapper=Path(producer_record['environment']['RUSTC_WRAPPER'])
 assert wrapper.name=='pump_physical_source_wrapper.py' and wrapper.parent.name=='scripts'
 file=Path(name)if Path(name).is_absolute()else wrapper.parent.parent/name
 file=file.resolve();relative=str(file.relative_to(producer_root.resolve()));assert sha(file)==digest
 cp(file,Path('new-cache-provenance/primary')/relative);producer_primary[relative]=digest
checkpoint['cache_primary_source_sha256']=producer_primary
checkpoint['cache_primary_scope']='Hash-bound clean/cached/control source for external-cache qualification; final Rust-only variants are bound separately.'

checkpoint['repeat_build_kind']='Fresh main compilation using hash-verified external-only dependencies under the explicit linux-v1.44-sbpf hybrid profile; the profile-specific graph was independently rebuilt without cache and reproduced with its distinct verified cache key.'
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
cp(W/'round40-unified/state.json','queue-state.json')
for directory,names in [('work/parallel-main-migration-burn',['BURN-API-REVIEW.json','BURN-IDENTITY-EVIDENCE.json']),('work/parallel-main-legacy-buyback-split',['summary.json','NEW-CASES.json']),('work/parallel-main-sell-v2-buyback-accounting',['summary.json','NEW-CASES.json']),('work/parallel-main-v3-buyback-assert',['FINAL-RESULT02.json','EVIDENCE-MANIFEST02.json']),('work/parallel-main-v3-cost-order',['FOCUSED-RESULT.json','INCREMENTAL-CLI-MANIFEST.json']),('work/parallel-main-data-frontier',['LAYOUT-TRIAL.json','LAYOUT-RESULT.json','LAYOUT-REVIEW.json','SIGNED-LOG-SOURCE-MAPPINGS.json','SOURCE-PATHS.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for name in ['run_round40_full.py','main_corpus_runner_v3.py','finish_round40.py','package_round40.py','promote_round40.py','write_round40_readme.py','check_call_closure.py','unified-main-corpus-round40.json']:
 rel='work/parallel-main-integration/'+name;cp(ROOT/rel,Path('inputs')/rel)
 if rel.endswith('.py'):support[rel]=sha(ROOT/rel)
for log in (W/'round40-unified/suites').rglob('*.log'):
 cp(log,Path('validation-logs')/log.relative_to(W/'round40-unified/suites'))
if (W/'round40-initial-queue-failure.json').exists():cp(W/'round40-initial-queue-failure.json','initial-queue-failure.json')
cp(ROOT/'work/parallel-main-data-frontier/round40-source-path-fidelity.json','source-path-fidelity.json')
rel='work/parallel-main-data-frontier/audit_source_paths.py';cp(ROOT/rel,Path('inputs')/rel);support[rel]=sha(ROOT/rel)
for directory in ['work/parallel-main-v3-quote-validation-order','work/parallel-main-v3-quote-fee-tail','work/parallel-main-v3-quote-scanner','work/parallel-main-sweep-recipient-reuse','work/parallel-main-fee-math-module']:
 for f in (ROOT/directory).glob('*.py'):
  rel=str(f.relative_to(ROOT));cp(f,Path('inputs')/rel);support[rel]=sha(f)
for directory,names in [('work/parallel-main-migration-burn',['NATIVE-TRANSFER-REVIEW.json']),('work/parallel-main-v3-quote-fee-tail',['FINAL-RESULT.json','INCREMENTAL-CLI-MANIFEST.json']),('work/parallel-main-v3-quote-scanner',['PARSER-CLI-MANIFEST.json']),('work/parallel-main-sweep-recipient-reuse',['summary.json']),('work/parallel-main-fee-math-module',['summary.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
cp(ROOT/'work/parallel-main-data-frontier/round40-frontier.json','remaining-body-and-data-triage.json')
rel='work/parallel-main-data-frontier/analyze.py';cp(ROOT/rel,Path('inputs')/rel);support[rel]=sha(ROOT/rel)
cp(ROOT/'work/parallel-main-data-frontier/round40-location-objects.json','location-object-triage.json')
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
retention=read(W/'round40-transaction-retention.json')
assert retention['status']=='passed' and retention['counts']['fully_backed_pairs']==checkpoint['full_cases']+checkpoint['additional_cases']
cp(W/'round40-transaction-retention.json','transaction-retention.json')
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
for name in ['pump_text_layout.py','pump_text_layout_rustc.py','pump_text_layout_linker.py','pump_text_layout_default.ld','pump_data_order.py','pump_derive_data_order.py']:
 rel='scripts/'+name;cp(ROOT/rel,Path('inputs')/rel)
 if name.endswith('.py'):support[rel]=sha(ROOT/rel)
 else:checkpoint['additional_input_sha256'][rel]=sha(ROOT/rel)
assert sha(W/'round40-layout/ordered.ld')==sha(W/'round40-layout/text-order.ld')
cp(W/'round40-layout/text-order.ld','text-order.ld')
cp(W/'build-round40/ordered.ld','ordered.ld')
cp(ROOT/'work/parallel-main-verified-linker-validation/identity-order.ld','identity-text.ld')
checkpoint['text_section_order']='text-order.ld'
checkpoint['text_section_order_sha256']=sha(P/'text-order.ld')
checkpoint['combined_section_order']='ordered.ld'
checkpoint['combined_section_order_sha256']=sha(P/'ordered.ld')
checkpoint['identity_text_order']='identity-text.ld'
checkpoint['identity_text_order_sha256']=sha(P/'identity-text.ld')
for file in (W/'round40-layout').iterdir():
 if file.is_file():cp(file,Path('layout-proof')/file.name)
for file in ['RESULT.json','MANIFEST.json','README.md','V2-INPUTS.json','r28-translation.json']:
 cp(ROOT/'work/parallel-main-verified-linker-validation'/file,Path('layout-proof/validated-builder')/file)
cp(W/'LINKER-OPTION-ROOT-REVIEW.json','layout-proof/root-review.json')
cp(W/'round40-builder-installation.json','layout-proof/installation.json')
cp(W/'build-round40-identity/unstripped.so','layout-proof/baseline.so')
cp(W/'build-round40-identity/link/link.map','layout-proof/baseline.map')
cp(W/'build-round40/link/link.map','layout-proof/ordered.map')
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
layout_check=""" verify_data_artifacts(cp)
"""
start=script.index(" import importlib.util\n sys.path.insert(0,str(P/'layout-proof/tools'))")
end=script.index(" sys.path.insert(0,str(P/'inputs/scripts'))",start)
script=script[:start]+layout_check+script[end:]
verifier.write_text(script)
for directory,names in [('work/parallel-main-transfer-fee-boundary',['RESULT02.json','RESULT04.json','EVIDENCE-MANIFEST02.json','EVIDENCE-MANIFEST04.json','native-pre-fee02.patch','native-fee04-from02.patch','native-fee04-fromR28.patch']),('work/parallel-main-ata-drop',['ATA-FIXED-ARRAY-REVIEW02.json','ata-matching-info-count-from-pausable.patch']),('work/parallel-main-entrypoint-221',['LOCK-DIFF.json','DATA-DELTA.json','TEXT-AND-RELOCATION-DELTA.json','DIRECT-TRAIT-PARITY.json','FINAL-RESULT.json','MANIFEST.json'])]:
 for name in names:cp(ROOT/directory/name,Path('recovery-evidence')/Path(directory).name/name)
for file in Path(CFG['entrypoint_directory']).glob('*.py'):
 rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)
cp(W/'round40-build-config.json','build-config.json')
cp(W/'round40-lock-audit.json','lock-audit.json')
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
for name,directory in [('build.json',W/'build-round40'),('repeat-build.json',W/'build-round40-repeat')]:
 record=read(directory/'build-comparison.json');file=directory/'target-library-profile-files.json'
 assert record['target_library_profile']['cache_context']==profile_context
 assert sha(file)==record['target_library_profile']['file_manifest_sha256']
 cp(file,checkpoint['target_library_profile_manifests'][name])
for label,directory in [('clean',Path(CFG['producer'])),('cached',Path(CFG['consumer']))]:
 file=directory/'target-library-profile-files.json';record=read(directory/'build-comparison.json')
 assert sha(file)==record['target_library_profile']['file_manifest_sha256']
 cp(file,Path('new-cache-provenance')/label/file.name)
for source,dest in [('build-comparison.json','baseline-build.json'),('target-library-profile-files.json','baseline-target-library-profile-files.json')]:
 cp(W/'build-round40-identity'/source,Path('layout-proof')/dest)
cp(ROOT/'scripts/pump_linux_v144_sbpf_libraries.json','inputs/scripts/pump_linux_v144_sbpf_libraries.json')
checkpoint['additional_input_sha256']['scripts/pump_linux_v144_sbpf_libraries.json']=sha(ROOT/'scripts/pump_linux_v144_sbpf_libraries.json')
cp(ROOT/'scripts/pump_linux_v144_sbf_libraries.json','inputs/scripts/pump_linux_v144_sbf_libraries.json')
checkpoint['additional_input_sha256']['scripts/pump_linux_v144_sbf_libraries.json']=sha(ROOT/'scripts/pump_linux_v144_sbf_libraries.json')
for path in CFG['profile_provenance']:
 file=Path(path);cp(file,Path('profile-provenance')/file.name)
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

for name in ['ROUND40-PACKAGING-REVIEW.json','ROUND40-PACKAGING-APPROVED.json']:
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
# Retain accepted collection/distribution/claim evidence and the rejected QuoteControl control.
for folder in ['parallel-main-distribution-pending-fees','parallel-main-collection-rent','parallel-main-collection-rent-review','parallel-main-claim-boundary-review','parallel-main-quote-control-frontier']:
 for file in (ROOT/'work'/folder).iterdir():
  if file.is_file() and file.suffix in ['.json','.patch','.md']:
   cp(file,Path('recovery-evidence')/folder/file.name)
 for file in (ROOT/'work'/folder).glob('*.py'):
  rel=str(file.relative_to(ROOT));cp(file,Path('inputs')/rel);support[rel]=sha(file)
# Data-aware archive proof: old certificate bytes stay unchanged; replay is not admission.
archive_support=ROOT/'work/parallel-main-data-order-archive'
assert sha(archive_support/'MANIFEST.json')=='595e622529ea9fd5615c5704ca8d5cf20b08b9464377ad94f3717f708e1b0107','Reviewed archive support packet changed'
archive_manifest=read(archive_support/'MANIFEST.json')
for name in ['verify_archive.py','reproduction.py','README.md','RESULT.json','MANIFEST.json','CONTROLS.json','REPRODUCTION-CONTROLS.json','CLI-CONTROLS.json','POSITIVE-FINAL.json']:
 if name!='MANIFEST.json':assert sha(archive_support/name)==archive_manifest['files'][name]['sha256']
 cp(archive_support/name,Path('archive-support')/name)
checkpoint['archive_support_sha256']={name:sha(P/'archive-support'/name)for name in ['verify_archive.py','reproduction.py']}
for name in ['pump_build_verified.py','pump_text_layout.py','pump_data_order.py','pump_derive_data_order.py']:
 rel='scripts/'+name
 assert corpus['definition_sha256'][rel]==sha(ROOT/rel),'Builder helper missing from frozen corpus inputs'
 cp(ROOT/rel,Path('inputs')/rel);py[rel]=sha(ROOT/rel)
for name in ['DATA-ORDER-ROOT-REVIEW.json','round40-builder-installation.json']:
 cp(W/name,Path('data-order')/name)
for name in ['FINAL-RESULT.json','MANIFEST.json','MANIFEST-ADDENDUM.json','ARCHIVE-FLOW.md','COST-OBSERVATION.json']:
 cp(ROOT/'work/parallel-main-data-order-option'/name,Path('data-order/tooling-evidence')/name)
cp(W/'round40-layout/data-order-certificate.json','data-order/admitted-certificate.json')
cp(W/'build-round40/data-order-transformation.json','data-order/transformation.json')
cp(W/'build-round40/link/link.map','data-order/initial-final.map')
cp(W/'build-round40-identity/candidate.so','layout-proof/baseline-candidate.so')
cp(W/'build-round40-identity/build-attempt.json','layout-proof/baseline-attempt.json')
checkpoint['data_order']={'status':'passed','builds':{},'archive_replays':{}}
for name,directory,prefix in [('build.json',W/'build-round40','initial'),('repeat-build.json',W/'build-round40-repeat','repeat')]:
 record=read(directory/'build-comparison.json');proof=directory/'data-order-transformation.json'
 assert record['data_order']['status']=='passed'
 assert record['data_order']['certificate_sha256']==sha(P/'data-order/admitted-certificate.json')
 assert record['data_order']['transformation_sha256']==sha(proof)
 destination='data-order/'+prefix+'-transformation.json';cp(proof,destination)
 checkpoint['data_order']['builds'][name]={'certificate':'data-order/admitted-certificate.json','certificate_sha256':sha(P/'data-order/admitted-certificate.json'),'transformation':destination,'transformation_sha256':sha(P/destination)}
# Bind the six explicit artifacts to the outer checkpoint, never rewrite cert paths.
module_path=P/'archive-support/verify_archive.py'
spec=importlib.util.spec_from_file_location('packaging_data_archive',module_path);archive_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(archive_module)
cert=read(P/'data-order/admitted-certificate.json')
artifact_paths={'original_elf':ROOT/'evidence/original/pump/deployed.so','baseline_elf':P/'layout-proof/baseline.so','baseline_map':P/'layout-proof/baseline.map','final_elf':P/'unstripped.so','final_map':P/'data-order/initial-final.map','admitted_certificate':P/'data-order/admitted-certificate.json'}
bindings={'schema':1,'artifacts':{name:{'sha256':sha(path),'bytes':path.stat().st_size}for name,path in artifact_paths.items()},'tools':cert['payload']['implementation']}
(P/'data-order/archive-bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
proof=archive_module.verify_archive(**artifact_paths,bindings=P/'data-order/archive-bindings.json',bindings_sha256=sha(P/'data-order/archive-bindings.json'),tools_directory=P/'inputs/scripts')
(P/'data-order/archive-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
checkpoint['data_order']['archive_replays']['initial']={'baseline_elf':'layout-proof/baseline.so','baseline_map':'layout-proof/baseline.map','final_map':'data-order/initial-final.map','certificate':'data-order/admitted-certificate.json','certificate_sha256':sha(P/'data-order/admitted-certificate.json'),'bindings':'data-order/archive-bindings.json','bindings_sha256':sha(P/'data-order/archive-bindings.json'),'proof':'data-order/archive-proof.json'}
# Preserve exactly the reviewed final source/evidence set, including optional later additions.
for name,digest in read(W/'round40-integration-plan.json')['evidence_sha256'].items():
 assert sha(ROOT/name)==digest
 cp(ROOT/name,Path('recovery-evidence/round40')/name)

checkpoint['supporting_python_sha256']=support
(P/'CHECKPOINT.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
print(P);print({k:checkpoint[k]for k in ['normalized_windows','raw_windows','matched_text_bytes','full_cases','additional_cases']})
