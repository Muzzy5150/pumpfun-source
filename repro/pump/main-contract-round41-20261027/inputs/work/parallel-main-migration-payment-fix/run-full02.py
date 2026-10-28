from pathlib import Path
import concurrent.futures,gzip,json,subprocess,sys,time
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;C=P/'build02/candidate.so';W=R/'work/parallel-main-loader-optimized/pump_with_captured_loader.py'
sys.path.insert(0,str(R/'work/parallel-main-v3-buyback-assert'));from audit_invocations import audit_invocations
jobs=json.load(open(R/'work/parallel-main-migration-burn/manifest.json'))+json.load(open(R/'work/parallel-main-leaf-validation/focused-manifest.json'))+[{'name':'new','script':'work/parallel-main-migration-payment-fix/probe-new.py'},{'name':'negative','script':'work/parallel-main-migration-payment-fix/probe-negative-dedup.py'}];state={}
def run(job):
 name=job['name'];script=R/job['script'];out=P/(name+'02.json.gz');cmd=[sys.executable,str(W),'--receipt',str(P/(name+'02.loader.json')),str(script),'--candidate',str(C),'--output',str(out)];t=time.monotonic()
 with(P/(name+'02.log')).open('w')as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 code=r.returncode;count=0
 if code==0 and out.exists():
  b=out.read_bytes();j=json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b);count=j['case_count'];rows=j.get('cases',[])
  if j.get('mismatches')or any(x.get('mismatches')or x.get('different_fields')or x.get('mismatched_fields')for x in rows):code=1
  a=audit_invocations(j);(P/(name+'02.invocations.json')).write_text(json.dumps(a,indent=2)+'\n')
  if a['mismatches']:code=1
 return name,{'returncode':code,'process_returncode':r.returncode,'cases':count,'command':cmd,'output':str(out),'seconds':time.monotonic()-t}
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 for fut in concurrent.futures.as_completed([pool.submit(run,j)for j in jobs]):
  name,row=fut.result();state[name]=row;(P/'full-state02.json').write_text(json.dumps(state,indent=2)+'\n');print(name,row['returncode'],row['cases'],flush=True)
if any(r['returncode']for r in state.values()):raise SystemExit(1)
