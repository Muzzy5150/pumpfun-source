from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import gzip,json,subprocess,sys,time
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;B=P/'build01';start=time.monotonic()
while not(B/'build-comparison.json').exists():
 assert time.monotonic()-start<900;time.sleep(2)
build=json.load(open(B/'build-comparison.json'));assert build['returncode']==0 and build['source_unchanged']
commands=[('new22',[sys.executable,str(R/'work/parallel-main-unobserved-gates/probe.py'),'--family','cashback_accounts','--candidate',str(B/'candidate.so'),'--output',str(P/'after01.json.gz')]),('regression',[sys.executable,str(P/'regressions.py'),'--candidate',str(B/'candidate.so'),'--output',str(P/'regression01.json.gz')])]
def run(item):
 name,args=item
 with(P/(name+'.log')).open('w')as f:subprocess.run(args,cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)
 print(name,'finished',flush=True)
with ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(run,commands))
for name in ['after01','regression01']:
 d=json.load(gzip.open(P/(name+'.json.gz'),'rt'));assert not d['mismatches']and not d['diagnostics']['mismatches'],name;print(name,d['case_count'],'passed',flush=True)
subprocess.run([sys.executable,str(R/'work/pump-reserve-byte-recovery/inventory_current.py'),'--candidate',str(B/'unstripped.so'),'--output',str(P/'inventory.json')],cwd=R,check=True)
