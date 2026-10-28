"""Run one frozen main-Pump build through a single resumable queue and a fresh repeat build."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip, hashlib, json, shutil, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;B=W/'build-round28'
def read(path):
 data=path.read_bytes();return json.loads(gzip.decompress(data)if data[:2]==b'\x1f\x8b'else data)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
record=read(B/'build-comparison.json');assert record['returncode']==0 and record['source_unchanged']
burn=ROOT/'work/parallel-main-migration-burn/BURN-API-REVIEW.json'
assert sha(burn)=='d4047f104c4a499d75a34616d0edb53403b81590c42483d053e8441d018a587d'
assert read(burn)['runtime']['case_count']==1172 and not read(burn)['runtime']['mismatches']
plan=read(W/'round28-integration-plan.json')
assert plan['status']=='Frozen for combined validation'
assert all(sha(ROOT/plan['source_directory']/path)==digest for path,digest in plan['changes'].items())
state={'status':'running','candidate_sha256':record['comparison']['candidate_sha256'],'checks':{}}
reuse_repeat='--reuse-passed-repeat' in sys.argv
if reuse_repeat:
 previous=read(W/'round28-check-state.json')
 assert previous['candidate_sha256']==state['candidate_sha256']
 assert previous['checks']['repeat_build']['returncode']==0
 repeated=read(W/'build-round28-repeat/build-comparison.json')
 assert repeated['comparison']['candidate_sha256']==state['candidate_sha256']
 assert repeated['unstripped_sha256']==record['unstripped_sha256']
 state['checks']['repeat_build']=previous['checks']['repeat_build']
def save():
 path=W/'round28-check-state.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(path)
save()
def run(name,command):
 start=time.monotonic()
 with (W/f'round28-{name}.log').open('w')as log:result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 return name,{'returncode':result.returncode,'seconds':time.monotonic()-start,'command':command}
queue=W/'round28-unified'
unified=[sys.executable,str(W/'main_corpus_runner_v3.py'),'--manifest',str(W/'unified-main-corpus-round28.json'),'--build',str(B),'--output',str(queue),'--workers','8']
repeat=[sys.executable,str(ROOT/'scripts/pump_build_verified.py'),'--source-directory',str(W/'round28-source/programs/pump'),'--workspace-layout','--registry-home',str(ROOT/'work/parallel-main-create-sizing/build-direct-trait/cargo-home'),'--dependency-cache',str(ROOT/'work/parallel-main-cache/direct-cache'),'--output',str(W/'build-round28-repeat')]
with ThreadPoolExecutor(max_workers=2)as pool:
 jobs=[pool.submit(run,'unified',unified)]
 if not reuse_repeat:jobs.append(pool.submit(run,'repeat_build',repeat))
 for future in as_completed(jobs):
  name,row=future.result();state['checks'][name]=row;save();print(name,row['returncode'],flush=True)
if state['checks']['unified']['returncode'] and (queue/'state.json').exists():
 current=read(queue/'state.json');failures=current['failures']
 explicit=True
 for failure in failures:
  group,name=failure['key'].split('.',1);attempt=current['attempts'][failure['key']]
  log=(queue/'suites'/group/f'{name}.attempt{attempt}.log').read_text()
  explicit &= 'Too many open files' in log
 if failures and explicit:
  shutil.copy2(queue/'state.json',W/'round28-initial-queue-failure.json');time.sleep(5)
  name,row=run('unified_resource_retry',unified[:-1]+['1','--resume']);state['checks'][name]=row;state['checks']['unified']=row;save()
if any(row['returncode']for row in state['checks'].values()):
 state['status']='failed';save();raise RuntimeError('Incomplete checks; inspect retained per-suite state and logs.')
full=read(queue/'full.json.gz');extra=read(queue/'additional.json.gz')
assert full['case_count']==10468 and full['suite_count']==44 and not full['diagnostics']['mismatches']
assert extra['case_count']==6522 and extra['suite_count']==133 and not extra['diagnostics']['mismatches']
assert full['candidate_sha256']==extra['candidate_sha256']==record['comparison']['candidate_sha256']
shutil.copy2(queue/'full.json.gz',W/'round28-captured-full.json.gz');shutil.copy2(queue/'additional.json.gz',W/'round28-captured-additional.json.gz')
retention_command=[sys.executable,str(ROOT/'work/parallel-main-receipt-verifier/verify_receipts.py'),'--full',str(W/'round28-captured-full.json.gz'),'--additional',str(W/'round28-captured-additional.json.gz'),'--root',str(ROOT),'--candidate-sha256',record['comparison']['candidate_sha256'],'--expected-total','16990','--output',str(W/'round28-transaction-retention.json')]
name,row=run('transaction_retention',retention_command);state['checks'][name]=row;save()
if row['returncode']:
 state['status']='failed';save();raise RuntimeError('Complete transaction retention audit failed')
state['status']='passed';state['case_count']=full['case_count']+extra['case_count'];save();print(state,flush=True)
