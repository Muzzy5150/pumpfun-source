"""Verify one frozen main-Pump composition with cached and clean builds and bounded signed corpora."""
from pathlib import Path
import concurrent.futures,json,subprocess,sys,time,shutil
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;B=W/'build-round21';start=time.monotonic();state={'status':'waiting_for_build','checks':{}}
def save():(W/'round21-check-state.json').write_text(json.dumps(state,indent=2)+'\n')
save()
while True:
 try:r=json.loads((B/'build-comparison.json').read_text());break
 except (FileNotFoundError,json.JSONDecodeError):
  if time.monotonic()-start>900:raise TimeoutError('build receipt unavailable')
  time.sleep(1)
assert r['returncode']==0 and r['source_unchanged'];state['candidate_sha256']=r['comparison']['candidate_sha256'];state['status']='critical';save();base=[sys.executable]
def run(name,cmd):
 t=time.monotonic()
 if name=='clean_build':
  while shutil.disk_usage(ROOT).free < 3*1024**3:
   print('clean_build waiting for3GiBfree',flush=True);time.sleep(5)
 with (W/f'round21-{name}.log').open('w')as f:x=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 return name,{'returncode':x.returncode,'seconds':time.monotonic()-t,'command':cmd}
state['status']='full_validation';save();candidate=B/'candidate.so';source=r['source_directory'];jobs={
 'full':base+[str(W/'validate_optimized_loader.py'),'--candidate',str(candidate),'--source-directory',source,'--build-comparison',str(B/'build-comparison.json'),'--output',str(W/'round21-captured-full.json.gz'),'--workers','4','--captured-loader'],
 'additional':base+[str(W/'validate_additional_round21.py'),'--candidate',str(candidate),'--source-directory',source,'--build-comparison',str(B/'build-comparison.json'),'--output',str(W/'round21-captured-additional.json.gz'),'--workers','4'],
 'repeat_build':base+[str(ROOT/'scripts/pump_build_verified.py'),'--source-directory',str(W/'round21-source/programs/pump'),'--workspace-layout','--registry-home',str(ROOT/'work/parallel-main-create-sizing/build-direct-trait/cargo-home'),'--dependency-cache',str(ROOT/'work/parallel-main-cache/direct-cache'),'--output',str(W/'build-round21-repeat')],
 'inventory':base+[str(ROOT/'work/pump-reserve-byte-recovery/inventory_current.py'),'--candidate',str(B/'unstripped.so'),'--output',str(B/'normalized-inventory.json')],
}
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
 for f in concurrent.futures.as_completed([pool.submit(run,n,c)for n,c in jobs.items()]):
  n,row=f.result();state['checks'][n]=row;save();print(n,row['returncode'],round(row['seconds'],2),flush=True)
state['status']='passed'if all(x['returncode']==0 for x in state['checks'].values())else'failed';save();assert state['status']=='passed'
