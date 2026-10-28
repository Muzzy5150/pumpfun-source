from pathlib import Path
import hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
producer=P/'build-direct-trait';cached=P/'build-direct-trait-cached02';out=P/'build-direct-trait-checked';target=producer/'target';hidden=producer/'target-hidden-for-proof'
left=json.loads((producer/'build-comparison.json').read_text());right=json.loads((cached/'build-comparison.json').read_text())
for name in ['candidate.so','unstripped.so']:assert sha(producer/name)==sha(cached/name),name
assert target.is_dir()and not target.is_symlink()and not hidden.exists()and not out.exists()
active=subprocess.run(['ps','-axo','pid,args'],text=True,capture_output=True,check=True).stdout.splitlines();assert not any(str(target)in x and int(x.split(None,1)[0])!=os.getpid()for x in active)
inputs={str(producer/f):sha(producer/f)for f in ['candidate.so','unstripped.so','build-comparison.json']}
command=[sys.executable,str(ROOT/'scripts/pump_build_verified.py'),'--source-directory',str(P/'source-direct-trait-checked'),'--workspace-layout','--registry-home',str(producer/'cargo-home'),'--dependency-cache',str(ROOT/'work/parallel-main-cache/direct-cache'),'--output',str(out)]
start=time.monotonic();target.rename(hidden);result=None;absent_after=False
try:
 assert not target.exists()
 with (P/'build-direct-trait-checked.log').open('w')as log:result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 absent_after=not target.exists();assert absent_after
finally:
 assert hidden.exists()and not target.exists();hidden.rename(target)
 assert inputs=={k:sha(k)for k in inputs}
 receipt={'scope':'Fresh main compile from new dependency cache while original clean producer target path is absent; reversible rename restored unchanged producer outputs.','producer_target':str(target),'hidden_target':str(hidden),'producer_original_path_absent_before_and_after_child':absent_after,'producer_restored':target.is_dir(),'producer_files_sha256':inputs,'command':command,'returncode':result.returncode if result else None,'elapsed_seconds':time.monotonic()-start}
 if (out/'build-comparison.json').exists():receipt['child_build_sha256']=sha(out/'build-comparison.json')
 (P/'PRODUCER-INDEPENDENT.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert result and result.returncode==0
print('producer-independent checked-source build passed')
