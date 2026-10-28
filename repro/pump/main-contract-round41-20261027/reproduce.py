#!/usr/bin/env python3
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
