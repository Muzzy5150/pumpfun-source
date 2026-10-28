#!/usr/bin/env python3
"""Plan fresh archive reproduction and verify its final receipts; never run a compiler."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('archive_verifier',HERE/'verify_archive.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
sha=v.sha;require=v.require

def source_files(root):
    root=Path(root).resolve()
    return {str(p.relative_to(root)):sha(p)for p in sorted(root.rglob('*'))if p.is_file()and not {'.git','target','__pycache__'}.intersection(p.relative_to(root).parts)}

def plan_reproduction(request):
    """Return argv arrays only. Inputs/recipes are checked; no build is launched."""
    require(__debug__,'reproduction planning requires Python assertions enabled')
    keys={'schema','python','tools_directory','primary_source','primary_files','sdk','registry_home','dependency_cache','target_library_directory','original_elf','archive_bindings','archive_bindings_sha256','identity_text_order','pure_text_order','pure_text_order_sha256','output_root','expected_elf_sha256'}
    require(set(request)==keys and request['schema']==1,'invalid reproduction request')
    r=dict(request)
    for k in ['python','tools_directory','primary_source','sdk','registry_home','dependency_cache','target_library_directory','original_elf','archive_bindings','identity_text_order','pure_text_order','output_root']:r[k]=str(Path(r[k]).resolve())
    require(not Path(r['output_root']).exists(),'reproduction output root must be new')
    require(Path(r['python']).is_file(),'Python executable missing')
    require((Path(r['primary_source'])/'Cargo.toml').is_file(),'archived primary manifest missing')
    require(source_files(r['primary_source'])==r['primary_files'],'archived primary source differs')
    require(sha(r['archive_bindings'])==r['archive_bindings_sha256'],'archive bindings digest differs')
    bindings=json.loads(Path(r['archive_bindings']).read_text())
    require(sha(r['original_elf'])==v.ORIGINAL_SHA,'original main-Pump ELF differs')
    require(sha(r['pure_text_order'])==r['pure_text_order_sha256'],'archived pure text recipe differs')
    expected=r['expected_elf_sha256']
    require(set(expected)=={'candidate.so','unstripped.so'} and all(re.fullmatch('[0-9a-f]{64}',x)for x in expected.values()),'two expected ELF hashes required')
    with v.tools_context(r['tools_directory'],bindings['tools'],r['original_elf'])as helper:
        layout=__import__('pump_text_layout')
        default=(helper.HERE/'pump_text_layout_default.ld').read_text()
        pure=Path(r['pure_text_order']).read_text()
        try:layout.check_script(default,pure)
        except AssertionError as e:raise v.VerificationError('invalid pure text recipe')from e
        identity=Path(r['identity_text_order']).read_text()
        try:layout.check_script(default,identity)
        except AssertionError as e:raise v.VerificationError('invalid identity text recipe')from e
        canonical=default.replace(layout.RULE,'  .text : {\n\n    *(.text*)\n  } :text')
        require(identity==canonical,'identity recipe has non-identity selectors')
    tools=Path(r['tools_directory']);out=Path(r['output_root'])
    common=[r['python'],str(tools/'pump_build_verified.py'),'--source-directory',r['primary_source'],'--workspace-layout','--sdk',r['sdk'],'--registry-home',r['registry_home'],'--dependency-cache',r['dependency_cache'],'--target-library-profile','linux-v1.44-sbf','--target-library-directory',r['target_library_directory']]
    steps=[{'name':'fresh_identity','argv':common+['--text-section-order',r['identity_text_order'],'--output',str(out/'identity')]},
           {'name':'new_source_specific_certificate','argv':[r['python'],str(tools/'pump_derive_data_order.py'),'--baseline-build',str(out/'identity'),'--text-section-order',r['pure_text_order'],'--output',str(out/'data-order-certificate.json')]},
           {'name':'fresh_final','argv':common+['--text-section-order',r['pure_text_order'],'--data-order-certificate',str(out/'data-order-certificate.json'),'--output',str(out/'final')]},
           {'name':'both_expected_ELF_hashes_and_receipts','argv':[r['python'],str(HERE/'reproduction.py'),'verify-final','--build',str(out/'final'),'--certificate',str(out/'data-order-certificate.json'),'--candidate-sha256',expected['candidate.so'],'--unstripped-sha256',expected['unstripped.so'],'--output',str(out/'FINAL-HASH-PROOF.json')]}]
    return {'scope':__doc__,'status':'planned_not_executed','fresh_admission_required':True,'old_certificate_reused':False,'steps':steps,'expected_elf_sha256':expected,'primary_source_sha256':r['primary_files'],'pure_text_order_sha256':r['pure_text_order_sha256'],'identity_text_order_sha256':sha(r['identity_text_order']),'tool_sha256':{p.name:sha(p)for p in sorted(tools.iterdir())if p.is_file()},'requirements':['The tool directory must be installed in the complete archived repository/helper layout expected by the verified builder; planning does not execute or authenticate a compiler.','Use a correctly keyed verified external-only cache. If absent, establish a genuine ordinary clean producer and parity proof first. Never relabel an old cache.','The original admitted certificate remains immutable provenance. The three build/derive steps create a new certificate from the fresh identity.','After final hash/receipt verification, replay the archive transformation using explicit fresh identity/final paths and run required runtime/transaction receipt gates.']}

def verify_final(build, certificate, expected):
    """Require both reproduced ELF hashes and standard successful data receipts."""
    require(__debug__,'final verification requires Python assertions enabled')
    build=Path(build).resolve();certificate=Path(certificate).resolve()
    require(set(expected)=={'candidate.so','unstripped.so'},'two expected ELF hashes required')
    actual={name:sha(build/name)for name in expected}
    require(actual==expected,'reproduced ELF hashes differ')
    records={name:json.loads((build/name).read_text())for name in ['build-attempt.json','build-comparison.json']}
    transform_path=build/'data-order-transformation.json';transform=json.loads(transform_path.read_text())
    for name,r in records.items():
        require(r['returncode']==0 and r['source_unchanged'],'unsuccessful reproduction receipt: '+name)
        require(r['dependency_cache']['main_freshly_compiled'],'main was not freshly compiled: '+name)
        require(r['unstripped_sha256']==actual['unstripped.so'] and r['comparison']['candidate_sha256']==actual['candidate.so'],'receipt ELF binding differs: '+name)
        require(r['data_order']['status']=='passed','data-order status is not passed: '+name)
        require(r['data_order']['certificate_sha256']==sha(certificate),'new certificate receipt binding differs: '+name)
        require(r['data_order']['transformation_sha256']==sha(transform_path),'transformation receipt binding differs: '+name)
    require(transform['status']=='passed' and transform['candidate_sha256']==actual['unstripped.so'],'transformation ELF binding differs')
    return {'status':'passed','scope':'Both final ELF hashes and standard completed data-order build receipts, without compiling.','actual_elf_sha256':actual,'certificate_sha256':sha(certificate),'records_sha256':{name:sha(build/name)for name in records},'transformation_sha256':sha(transform_path),'runtime_reexecuted':False,'fresh_admission_reexecuted_by_this_function':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('plan');a.add_argument('--request',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    a=s.add_parser('verify-final');a.add_argument('--build',type=Path,required=True);a.add_argument('--certificate',type=Path,required=True);a.add_argument('--candidate-sha256',required=True);a.add_argument('--unstripped-sha256',required=True);a.add_argument('--output',type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'use a new output')
    result=plan_reproduction(json.loads(a.request.read_text()))if a.mode=='plan'else verify_final(a.build,a.certificate,{'candidate.so':a.candidate_sha256,'unstripped.so':a.unstripped_sha256})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'output':str(a.output)}))
if __name__=='__main__':main()
