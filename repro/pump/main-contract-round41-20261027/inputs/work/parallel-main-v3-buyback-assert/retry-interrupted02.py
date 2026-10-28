from pathlib import Path
import subprocess,sys,json,gzip,time
P=Path(__file__).resolve().parent;R=P.parents[1];C=P/'build02/candidate.so';W=R/'work/parallel-main-loader-optimized/pump_with_captured_loader.py'
saved=json.loads((P/'regression-state.json').read_text());retries={}
for name in ['v3-precedence','multihop-native','sell-v2-guards']:
 row=saved[name];cmd=row['command'][:];out=P/(name+'-retry1'+Path(row['output']).suffix);idx=cmd.index('--output');cmd[idx+1]=str(out)
 if '--receipt' in cmd:cmd[cmd.index('--receipt')+1]=str(P/(name+'-retry1.loader.json'))
 t=time.monotonic()
 with (P/(name+'-retry1.log')).open('w')as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 result={'command':cmd,'output':str(out),'returncode':r.returncode,'seconds':time.monotonic()-t}
 if r.returncode==0:
  b=out.read_bytes();d=json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
  result.update(case_count=d.get('case_count',len(d.get('cases',[]))),mismatches=d.get('mismatches',[]),diagnostics=d.get('diagnostics',{}))
 retries[name]=result;(P/'retry-state02.json').write_text(json.dumps(retries,indent=2)+'\n');print(name,result['returncode'],flush=True)
 if result['returncode']!=0:raise SystemExit(result['returncode'])
