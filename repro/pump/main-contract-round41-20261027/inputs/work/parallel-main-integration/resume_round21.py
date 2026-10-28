"""Resume the interrupted Round21 corpus without rebuilding or losing completed cases."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip, hashlib, json, shutil, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
def read(path):
 data=path.read_bytes();return json.loads(gzip.decompress(data) if data[:2]==b'\x1f\x8b' else data)
state=read(W/'round21-check-state.json')
state['initial_checks']=state['checks'].copy();state['status']='resuming_after_host_enfile'
state['resume_reason']='Host file-open errors and contemporaneous standard-library import failures. Initial completed receipts are validated and retained; missing suites are rerun with lower process concurrency.'
def save():(W/'round21-check-state.json').write_text(json.dumps(state,indent=2)+'\n')
save();B=W/'build-round21';record=read(B/'build-comparison.json')
jobs={
 'full':[sys.executable,str(W/'validate_full_resumed21.py'),'--candidate',str(B/'candidate.so'),'--source-directory',record['source_directory'],'--build-comparison',str(B/'build-comparison.json'),'--output',str(W/'round21-resumed-full.json.gz'),'--workers','2','--captured-loader'],
 'additional':[sys.executable,str(W/'validate_additional_resumed21.py'),'--candidate',str(B/'candidate.so'),'--source-directory',record['source_directory'],'--build-comparison',str(B/'build-comparison.json'),'--output',str(W/'round21-resumed-additional.json.gz'),'--workers','2'],
}
def run(name,cmd):
 start=time.monotonic()
 with (W/f'round21-resumed-{name}.log').open('w') as log:
  result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 return name,{'returncode':result.returncode,'seconds':time.monotonic()-start,'command':cmd}
with ThreadPoolExecutor(max_workers=2) as pool:
 for future in as_completed([pool.submit(run,name,cmd)for name,cmd in jobs.items()]):
  name,row=future.result();state['checks'][name]=row;save();print(name,row['returncode'],flush=True)
if any(row['returncode'] for row in state['checks'].values()):
 state['status']='resume_failed';save();raise RuntimeError('Resumed corpus did not complete; all evidence retained.')
full=read(W/'round21-resumed-full.json.gz');extra=read(W/'round21-resumed-additional.json.gz')
assert full['case_count']==10468 and len(full['suites'])==44 and not full['diagnostics']['mismatches']
assert extra['case_count']==5498 and extra['suite_count']==99 and not extra['diagnostics']['mismatches']
assert full['candidate_sha256']==extra['candidate_sha256']==record['comparison']['candidate_sha256']
for family in ['full','additional']:
 shutil.copy2(W/f'round21-resumed-{family}.json.gz',W/f'round21-captured-{family}.json.gz')
resume={'scope':__doc__,'candidate_sha256':record['comparison']['candidate_sha256'],'reused_suites':{'full':full['reused_completed_suites'],'additional':extra['reused_completed_suites']},'case_count':full['case_count']+extra['case_count'],'complete':True,'initial_failure_preserved':True}
(W/'round21-resume-proof.json').write_text(json.dumps(resume,indent=2)+'\n')
state['status']='passed';save();print(resume,flush=True)
