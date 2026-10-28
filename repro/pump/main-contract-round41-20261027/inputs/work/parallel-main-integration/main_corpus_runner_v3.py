"""Run the unchanged main-Pump corpora through one bounded, resumable work queue with up to eight workers."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse, gzip, hashlib, importlib.util, json, os, subprocess, sys, time, traceback

ROOT=Path(__file__).resolve().parents[2]
W=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from pump_diagnostic_audit import audit
spec=importlib.util.spec_from_file_location('full_corpus_validation',W/'validate_optimized_loader.py')
full_validation=importlib.util.module_from_spec(spec);spec.loader.exec_module(full_validation)
audit_path=ROOT/'work/parallel-main-v3-buyback-assert/audit_invocations.py'
audit_spec=importlib.util.spec_from_file_location('invocation_order_audit',audit_path)
invocation_module=importlib.util.module_from_spec(audit_spec);audit_spec.loader.exec_module(invocation_module)
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    data=Path(path).read_bytes()
    return json.loads(gzip.decompress(data)if data[:2]==b'\x1f\x8b'else data)
def write(path,value):
    path=Path(path);temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n');os.replace(temporary,path)
def differences(value,label):
    if isinstance(value,dict):
        for name,item in value.items():
            if name in ['different_fields','differences','mismatches','failures']:
                assert not item,(label,name,item)
            else:differences(item,label)
    elif isinstance(value,list):
        for item in value:differences(item,label)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,choices=range(1,9),default=8)
    p.add_argument('--resume',action='store_true')
    p.add_argument('--plan-only',action='store_true')
    p.add_argument('--only',action='append',default=[],help='Smoke-test exact group.name keys; never produces full corpus reports.')
    a=p.parse_args();a.output=a.output.resolve();a.build=a.build.resolve()
    manifest=read(a.manifest);build=read(a.build/'build-comparison.json')
    candidate=a.build/'candidate.so';original=ROOT/'evidence/original/pump/deployed.so'
    assert build['returncode']==0 and build['source_unchanged']
    assert sha(candidate)==build['comparison']['candidate_sha256']
    inputs={str(path.resolve()):sha(path)for path in [Path(__file__),audit_path,a.manifest,a.build/'build-comparison.json',candidate,original,W/'validate_optimized_loader.py',W/'validate_combined.py',ROOT/'scripts/pump_diagnostic_audit.py',ROOT/'work/parallel-main-loader-optimized/pump_with_captured_loader.py',ROOT/'work/parallel-main-loader-optimized/pump_captured_loader.py']}
    for path,digest in manifest['definition_sha256'].items():
        assert sha(ROOT/path)==digest;inputs[str(ROOT/path)]=digest
    suites={row['group']+'.'+row['name']:row for row in manifest['suites']}
    assert len(suites)==len(manifest['suites'])
    for row in suites.values():inputs[str(ROOT/row['script'])]=sha(ROOT/row['script'])
    def check_inputs():
        assert all(sha(path)==digest for path,digest in inputs.items())
        assert all(sha(ROOT/path)==digest for path,digest in build['source_sha256'].items())
    check_inputs()
    totals={group:sum(row['cases']for row in suites.values()if row['group']==group)for group in ['full','additional']}
    assert totals==manifest['counts']
    if a.plan_only:
        print({'suites':len(suites),'counts':totals,'workers':a.workers});return
    selected=set(a.only)if a.only else set(suites)
    assert selected<=suites.keys()
    a.output.mkdir(parents=True,exist_ok=a.resume)
    state_path=a.output/'state.json'
    if a.resume:
        state=read(state_path)
        assert state['candidate_sha256']==sha(candidate) and state['input_sha256']==inputs
        assert set(state['selected'])==selected
    else:
        state={'status':'running','candidate_sha256':sha(candidate),'input_sha256':inputs,'selected':sorted(selected),'completed':{},'attempts':{},'failures':[]}
    state['status']='running';write(state_path,state)
    wrapper=ROOT/'work/parallel-main-loader-optimized/pump_with_captured_loader.py'
    def verify(key,path,loader):
        row=suites[key];result=read(path)
        if row['group']=='full':count=full_validation.validate_result(row['name'],result,candidate,original)
        else:
            count=result['case_count']if 'case_count'in result else (result['cases']if isinstance(result.get('cases'),int)else len(result.get('cases',[])))
            differences(result,key)
        assert count==row['cases'],(key,count,row['cases'])
        diagnostic=audit({row['name']:result});assert not diagnostic['mismatches'],(key,diagnostic['mismatches'])
        invocations=invocation_module.audit_invocations(result);assert invocations['paired_cases']==count,(key,'invocation audit coverage',invocations['paired_cases'],count);assert not invocations['mismatches'],(key,'invocation_order',invocations['mismatches'])
        result['invocation_audit']=invocations
        receipt=read(loader);assert receipt['loads']
        assert {item['elf_sha256']for item in receipt['loads']}=={sha(candidate),sha(original)}
        assert all(item['program_bytes']==36 and item['program_owner']=='BPFLoaderUpgradeab1e11111111111111111111111' and item['programdata_bytes']==10485760 and item['elf_prefix_unchanged'] and item['zero_allocation_tail']for item in receipt['loads'])
        assert all(sha(name)==digest for name,digest in receipt['input_sha256'].items())
        return result
    results={}
    for key,saved in state['completed'].items():
        assert sha(saved['output'])==saved['result_sha256'] and sha(saved['loader'])==saved['loader_sha256']
        results[key]=verify(key,Path(saved['output']),Path(saved['loader']))
    def run(key,attempt):
        row=suites[key];directory=a.output/'suites'/row['group'];directory.mkdir(parents=True,exist_ok=True)
        prefix=directory/(row['name']+f'.attempt{attempt}')
        output=prefix.with_suffix(prefix.suffix+'.json.gz');loader=prefix.with_suffix(prefix.suffix+'.loader.json');log=prefix.with_suffix(prefix.suffix+'.log')
        command=[sys.executable,str(wrapper),'--receipt',str(loader),str(ROOT/row['script']),'--candidate',str(candidate),'--output',str(output),*row.get('args',[])]
        text=(ROOT/row['script']).read_text()
        if "'--source-directory'"in text or'"--source-directory"'in text:command+=['--source-directory',build['source_directory']]
        start=time.monotonic()
        with log.open('w')as stream:subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
        result=verify(key,output,loader);check_inputs()
        saved={'name':row['name'],'group':row['group'],'case_count':row['cases'],'script_sha256':inputs[str(ROOT/row['script'])],'output':str(output),'loader':str(loader),'result_sha256':sha(output),'loader_sha256':sha(loader),'command':command,'seconds':time.monotonic()-start,'attempt':attempt}
        return key,result,saved
    pending=sorted(selected-results.keys(),key=lambda key:(-suites[key]['cases'],key))
    with ThreadPoolExecutor(max_workers=a.workers)as pool:
        jobs={}
        for key in pending:
            attempt=state['attempts'].get(key,0)+1;state['attempts'][key]=attempt
            jobs[pool.submit(run,key,attempt)]=key
        write(state_path,state)
        errors=[]
        for future in as_completed(jobs):
            if future.cancelled():continue
            try:
                key,result,saved=future.result();results[key]=result;state['completed'][key]=saved
                print({'completed':key,'cases':saved['case_count'],'remaining':len(selected-results.keys())},flush=True)
            except Exception as exc:
                failure={'key':jobs[future],'error':repr(exc),'traceback':traceback.format_exc()};errors.append(failure);state['failures'].append(failure)
                print({'failed':jobs[future],'error':repr(exc)},flush=True)
                for item in jobs:item.cancel()
            write(state_path,state)
    if errors:
        state['status']='failed';write(state_path,state);raise RuntimeError('Incomplete corpus; resume retains validated suite results and all failed attempts.')
    check_inputs();assert results.keys()==selected
    if a.only:
        state['status']='partial_smoke_passed';write(state_path,state);print({'partial':True,'passed':sorted(selected)});return
    for group in ['full','additional']:
        group_suites={row['name']:results[key]for key,row in suites.items()if row['group']==group}
        diagnostic=audit(group_suites);assert not diagnostic['mismatches']
        saved=[state['completed'][key]for key,row in suites.items()if row['group']==group]
        report={'scope':__doc__,'loader_profile':'captured-upgradeable','candidate_sha256':sha(candidate),'original_sha256':sha(original),'compiled_source_sha256':build['source_sha256'],'bound_files_sha256':inputs,'input_sha256':inputs,'script_sha256':{row['script']:inputs[str(ROOT/row['script'])]for row in suites.values()if row['group']==group},'suite_count':len(group_suites),'case_count':sum(row['case_count']for row in saved),'diagnostics':diagnostic,'mismatches':diagnostic['mismatches'],'results':saved,'loader_receipts':{row['name']:{'path':row['loader'],'sha256':row['loader_sha256']}for row in saved},'suites':group_suites}
        assert report['case_count']==totals[group]
        (a.output/f'{group}.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    state['status']='passed';write(state_path,state);print({'passed':True,'counts':totals,'workers':a.workers})
if __name__=='__main__':main()
