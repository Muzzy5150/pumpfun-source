from pathlib import Path
import concurrent.futures,gzip,json,subprocess,sys,time
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;C=P/'build01/candidate.so';W=R/'work/parallel-main-loader-optimized/pump_with_captured_loader.py'
sys.path.insert(0,str(R/'work/parallel-main-v3-buyback-assert'));from audit_invocations import audit_invocations
jobs=[('native',R/'repro/pump/native-curve-partial-fortyeight/harness/pump_multi_hop_curve_differential.py',[]),('two-curve',R/'scripts/pump_tokenkeg_two_curve_differential.py',['--source-directory',str(P/'build01/source/programs/pump'),'--build-report',str(P/'build01/build-comparison.json')]),('flags',R/'work/parallel-main-v3-validity/probe_multihop_flags.py',[]),('continuation',R/'work/parallel-main-v3-post-budget/probe-multihop-continuation.py',[]),('native-lamports',P/'probe-native-lamports.py',[])]
state={}
def run(job):
 name,script,extra=job;out=P/(name+'01.json.gz');cmd=[sys.executable,str(W),'--receipt',str(P/(name+'01.loader.json')),str(script),'--candidate',str(C),'--output',str(out),*extra];t=time.monotonic()
 with(P/(name+'01.log')).open('w')as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 code=r.returncode;count=0
 if code==0 and out.exists():
  b=out.read_bytes();j=json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b);count=j['case_count']
  if j.get('mismatches')or any(r.get('mismatches')or r.get('different_fields')for r in j['cases']):code=1
  a=audit_invocations(j);(P/(name+'01.invocations.json')).write_text(json.dumps(a,indent=2)+'\n')
  if a['mismatches']:code=1
 return name,{'returncode':code,'process_returncode':r.returncode,'cases':count,'command':cmd,'output':str(out),'seconds':time.monotonic()-t}
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 for fut in concurrent.futures.as_completed([pool.submit(run,j)for j in jobs]):
  name,row=fut.result();state[name]=row;(P/'runtime-state01.json').write_text(json.dumps(state,indent=2)+'\n');print(name,row['returncode'],row['cases'],flush=True)
if any(r['returncode']for r in state.values()):raise SystemExit(1)
