"""Finish the interrupted full corpus with one worker and explicit harness-bound reuse."""
from pathlib import Path
import gzip, json, shutil, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
def read(path):
 data=path.read_bytes();return json.loads(gzip.decompress(data)if data[:2]==b'\x1f\x8b'else data)
state=read(W/'round21-check-state.json');state['previous_resume_checks']=state['checks'].copy();state['status']='resuming_full_sequentially'
def save():(W/'round21-check-state.json').write_text(json.dumps(state,indent=2)+'\n')
save();B=W/'build-round21';record=read(B/'build-comparison.json')
command=[sys.executable,str(W/'validate_full_resumed21_tail.py'),'--candidate',str(B/'candidate.so'),'--source-directory',record['source_directory'],'--build-comparison',str(B/'build-comparison.json'),'--output',str(W/'round21-final-full.json.gz'),'--workers','1','--captured-loader']
start=time.monotonic()
with (W/'round21-final-full.log').open('w')as log:result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
state['checks']['full']={'returncode':result.returncode,'seconds':time.monotonic()-start,'command':command};save()
if result.returncode:
 state['status']='sequential_resume_failed';save();raise RuntimeError('Sequential tail incomplete; all receipts retained.')
full=read(W/'round21-final-full.json.gz');extra=read(W/'round21-resumed-additional.json.gz')
assert full['case_count']==10468 and len(full['suites'])==44 and not full['diagnostics']['mismatches']
assert extra['case_count']==5498 and extra['suite_count']==99 and not extra['diagnostics']['mismatches']
assert full['candidate_sha256']==extra['candidate_sha256']==record['comparison']['candidate_sha256']
shutil.copy2(W/'round21-final-full.json.gz',W/'round21-captured-full.json.gz')
shutil.copy2(W/'round21-resumed-additional.json.gz',W/'round21-captured-additional.json.gz')
proof={'scope':__doc__,'complete':True,'candidate_sha256':record['comparison']['candidate_sha256'],'case_count':full['case_count']+extra['case_count'],'reused_full_suites':full['reused_completed_suites'],'reused_additional_suites':extra['reused_completed_suites'],'harness_binding_policy':'Only completed suites with an explicit matching primary script hash in their retained result were reused. Other prior results remain evidence but were rerun.','failure_records':['round21-captured-full.json.gz.failed.json','round21-captured-additional.json.gz.failed.json','round21-resumed-full.json.gz.failed.json']}
(W/'round21-resume-proof.json').write_text(json.dumps(proof,indent=2)+'\n');state['status']='passed';save();print(proof,flush=True)
