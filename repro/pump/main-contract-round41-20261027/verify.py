#!/usr/bin/env python3
"""Verify the bounded main-Pump checkpoint and recompute its actual byte claims."""
from pathlib import Path
import base64,gzip,hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=next(p for p in P.parents if (p/'evidence/original/pump/deployed.so').is_file());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def normalized_window_delta(previous,current):
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
 corpus=read(P/'inputs/work/parallel-main-integration/unified-main-corpus-round41.json')
 assert sha(P/'inputs/work/parallel-main-integration/unified-main-corpus-round41.json')==cp['frozen_corpus_sha256']
 expected=corpus_expectations(corpus)
 for group,rows in expected.items():
  assert cp[group+'_suites']==len(rows) and cp[group+'_cases']==corpus['counts'][group]
  verify_corpus_report(corpus,group,read(P/('full.json.gz'if group=='full'else'additional.json.gz')),{**cp['input_python_sha256'],**cp['supporting_python_sha256']})
 assert corpus_additions(read(P/'corpus/previous-round40.json'),corpus)==cp['case_addition_breakdown']
 assert normalized_window_delta(read(P/'prior-inventory.json.gz'),read(P/'inventory.json.gz'))==cp['normalized_delta_from_previous']
 import importlib.util,sys,tempfile
 ordinary_dir=P/'ordinary-logs'
 ordinary=read(ordinary_dir/'report.json')
 assert sha(ordinary_dir/'report.json')==cp['ordinary_logs']['report_sha256']
 assert sha(ordinary_dir/'mismatches.jsonl.gz')==cp['ordinary_logs']['mismatches_sha256']==ordinary['mismatches_sha256']
 for name,digest in cp['ordinary_logs']['implementation_sha256'].items():assert sha(ordinary_dir/name)==digest
 assert ordinary['implementation_sha256']=={name:cp['ordinary_logs']['implementation_sha256'][name]for name in ['audit.py','paired_receipt_reader.py']}
 assert set(ordinary['source_sha256'].values())=={sha(P/'full.json.gz'),sha(P/'additional.json.gz')}
 sys.path.insert(0,str(ordinary_dir))
 audit_spec=importlib.util.spec_from_file_location('archived_ordinary_log_audit',ordinary_dir/'audit.py')
 audit_module=importlib.util.module_from_spec(audit_spec);audit_spec.loader.exec_module(audit_module)
 with tempfile.TemporaryDirectory(prefix='pump-ordinary-logs-')as temp:
  temp=Path(temp);actual=audit_module.audit_inputs([(P/'full.json.gz',cp['full_cases']),(P/'additional.json.gz',cp['additional_cases'])],temp/'report.json',temp/'mismatches.jsonl.gz')
 assert actual['status']=='passed'and actual['counts'].get('non_filename_mismatches',0)==0
 for name in ['status','counts','families','families_by_suite']:assert actual[name]==ordinary[name],('Ordinary log audit changed',name)
 assert ordinary['counts']==cp['ordinary_logs']['counts']and ordinary['families']==cp['ordinary_logs']['families']

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


def main():
 manifest=read(P/'MANIFEST.json')
 actual={str(f.relative_to(P))for f in P.rglob('*')if f.is_file()}
 assert actual==set(manifest)|{'MANIFEST.json'}, 'Archive file inventory differs from manifest'
 for name,digest in manifest.items():
  assert not (P/name).is_symlink(),name
  assert sha(P/name)==digest,name
 cp=read(P/'CHECKPOINT.json');assert cp['goal_complete'] is False and cp['whole_elf_equal'] is False and cp['archived_recipe_reproduced'] is True
 verify_hybrid_profile(cp)
 original=ROOT/'evidence/original/pump/deployed.so';assert sha(original)==cp['original_sha256'];assert sha(P/'candidate.so')==cp['candidate_sha256'];assert sha(P/'unstripped.so')==cp['unstripped_sha256']
 for field,folder in [('source_sha256','source'),('primary_source_sha256','primary'),('input_python_sha256','inputs'),('supporting_python_sha256','inputs')]:
  for name,digest in cp.get(field,{}).items():assert sha(P/folder/name)==digest,(folder,name)
 for name in ['build.json','repeat-build.json','canonical-build.json','reproduced-build.json']:
  r=read(P/name);assert r['returncode']==0 and r['source_unchanged'];assert r['comparison']['candidate_sha256']==cp['candidate_sha256'];assert r['unstripped_sha256']==cp['unstripped_sha256'];assert r['comparison']['full_byte_equality'] is False
 verify_data_artifacts(cp)
 sys.path.insert(0,str(P/'inputs/scripts'))
 from pump_diagnostic_audit import audit
 from pump_compare_function_bytes import normalize,body
 from pump_quote_control_function_match import sections
 full,extra=read(P/'full.json.gz'),read(P/'additional.json.gz');assert full['candidate_sha256']==extra['candidate_sha256']==cp['candidate_sha256']
 assert len(full['suites'])==cp['full_suites'] and full['case_count']==cp['full_cases'];assert extra['suite_count']==cp['additional_suites']==len(extra['suites']) and extra['case_count']==cp['additional_cases']
 for report,expected in [(full,cp['full_log_cases']),(extra,cp['additional_log_cases'])]:
  a=audit(report['suites']);assert not a['mismatches'] and a['log_bearing_cases']==expected
 for name in cp['loader_receipts']:
  r=read(P/name);assert r['loads']
  for x in r['loads']:
   assert x['elf_sha256'] in [cp['candidate_sha256'],cp['original_sha256']];assert x['program_owner']=='BPFLoaderUpgradeab1e11111111111111111111111' and x['program_bytes']==36 and x['programdata_bytes']==10485760 and x['elf_prefix_unchanged'] and x['zero_allocation_tail']
 ob=original.read_bytes();cb=(P/'unstripped.so').read_bytes();os,cs=sections(ob),sections(cb);iv=read(P/'inventory.json.gz');assert iv['original_sha256']==cp['original_sha256'] and iv['candidate_sha256']==cp['unstripped_sha256'];pairs={};matched=raw_count=text_count=0
 ordered_windows=sorted(iv['windows'],key=lambda row:row['start'])
 cursor=os['.text']['addr']
 for row in ordered_windows:
  assert row['start']==cursor and row['bytes']>0 and row['bytes']%8==0
  cursor+=row['bytes']
 assert cursor==os['.text']['addr']+os['.text']['size']==os['.text']['addr']+cp['original_text_bytes']
 for window in iv['windows']:
  a,n=window['start'],window['bytes'];o=body(ob,os,a,n);on,oo=normalize(o,a,os);assert hashlib.sha256(o).hexdigest()==window['raw_sha256'];any_raw=False
  if window['normalized_matches']:matched+=1;text_count+=n
  for c in window['normalized_matches']:
   raw=body(cb,cs,c['start'],n);cn,co=normalize(raw,c['start'],cs);assert on==cn;pairs[(a,c['start'])]=(oo,co);any_raw|=o==raw
  assert any_raw==window['raw_match'];raw_count+=any_raw
 assert len(iv['windows'])==cp['original_windows'] and matched==cp['normalized_windows'] and raw_count==cp['raw_windows'] and text_count==cp['matched_text_bytes']
 closed=read(P/'closed-calls.json');closed_pairs={(x['original_start'],x['candidate_start'])for x in closed['pairs']};assert len({a for a,b in closed_pairs})==cp['closed_call_windows_without_data']
 for pair in closed_pairs:
  oo,co=pairs[pair];assert [(x['offset'],x['kind'])for x in oo]==[(x['offset'],x['kind'])for x in co];assert all(x['kind']=='direct-call'for x in oo);assert all((x['target'],y['target'])in closed_pairs for x,y in zip(oo,co))
 proof=read(P/'new-cache-provenance/DIRECT-TRAIT-PARITY.json')
 build_record=read(P/'build.json')
 assert proof['status']=='passed' and build_record['dependency_cache']['key']==proof['cache_key']
 assert sha(P/'dependency-cache-manifest.json')==proof['manifest_sha256']==build_record['dependency_cache']['manifest_sha256']
 for filename,values in proof['elf_hashes'].items():
  assert values['clean']==values['cached']
  for label in ['clean','cached']:assert sha(P/'new-cache-provenance'/label/filename)==values[label]
 for label in ['clean','cached']:
  record=read(P/'new-cache-provenance'/label/'build-comparison.json');assert record['returncode']==0 and record['source_unchanged']
 import importlib.util
 audit_path=P/'inputs/work/parallel-main-v3-buyback-assert/audit_invocations.py'
 audit_spec=importlib.util.spec_from_file_location('archived_invocation_audit',audit_path)
 audit_module=importlib.util.module_from_spec(audit_spec);audit_spec.loader.exec_module(audit_module)
 for report in [full,extra]:
  calls=audit_module.audit_invocations(report['suites']);assert not calls['mismatches'];assert calls['paired_cases']==report['case_count']
 import importlib.util
 receipt_spec=importlib.util.spec_from_file_location('complete_transaction_receipt_audit',P/'inputs/work/parallel-main-receipt-verifier/receipt_verifier.py')
 receipt_module=importlib.util.module_from_spec(receipt_spec);receipt_spec.loader.exec_module(receipt_module)
 assert sha(P/'inputs/evidence/upstream/pump.json')==cp['additional_input_sha256']['evidence/upstream/pump.json']
 retention=receipt_module.verify_reports(P/'full.json.gz',P/'additional.json.gz',P/'inputs/evidence/upstream/pump.json',root=ROOT,candidate_sha256=cp['candidate_sha256'],expected_total=cp['full_cases']+cp['additional_cases'])
 assert retention['status']=='passed' and retention['counts']['fully_backed_pairs']==cp['fully_serialized_pairs']
 assert retention['counts']['verified_result_objects']==cp['serialized_result_objects']==2*cp['fully_serialized_pairs']
 from solders.transaction import VersionedTransaction
 signed=set()
 def walk(x):
  if isinstance(x,dict):
   for key,value in x.items():
    if key=='transaction_base64'and isinstance(value,str):signed.add(value)
    else:walk(value)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(full['suites']);walk(extra['suites'])
 for s in signed:assert all(VersionedTransaction.from_bytes(base64.b64decode(s)).verify_with_results())
 print(json.dumps({'verified':True,'files':len(manifest),'full_cases':cp['full_cases'],'additional_cases':cp['additional_cases'],'paired_log_cases':cp['full_log_cases']+cp['additional_log_cases'],'distinct_signed_transactions_reverified':len(signed),'normalized_windows':matched,'raw_windows':raw_count,'matched_text_bytes':text_count,'direct_call_closed_windows_without_data':cp['closed_call_windows_without_data'],'whole_elf_equal':False,'goal_complete':False}))
if __name__=='__main__':main()
