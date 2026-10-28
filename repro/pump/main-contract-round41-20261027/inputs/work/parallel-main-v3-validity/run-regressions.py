from pathlib import Path
import concurrent.futures,subprocess,sys,json,time
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;C=P/'build/candidate.so';W=R/'work/parallel-main-loader-optimized/pump_with_captured_loader.py';V=R/'work/parallel-main-v3-fee-waiver';Q=R/'work/parallel-main-v3-post-ceil'
jobs=[('v3-focused',R/'work/parallel-main-global-fee-waiver/probe-v3.py',[]),('v3-order',V/'probe-order.py',[]),('v3-configured',R/'scripts/pump_v3_configured_fee_differential.py',[]),('v3-extensions',R/'scripts/pump_v3_token_extensions_differential.py',[]),('v3-continuation',R/'work/parallel-main-trading-contexts/probe_v3_continuation.py',['--require-match']),('v3-post-fees',R/'work/parallel-main-trading-contexts/probe_v3_post_fees.py',['--require-match']),('v3-native-buyback',R/'work/parallel-main-v3-user-constraints/probe_buyback.py',['--require-match']),('v3-token-buyback',R/'work/parallel-main-v3-user-constraints/probe_buyback_token.py',['--require-match']),('v3-crossing',V/'probe-waived-crossing.py',[]),('v3-matrix',V/'probe-crossing-matrix.py',[]),('price-divisible',Q/'probe.py',[]),('price-boundaries',Q/'probe-boundaries.py',[]),('v3-precedence',R/'work/parallel-main-v3-helpers/probe_precedence_extended.py',['--require-match']),('multihop-native',R/'repro/pump/native-curve-partial-fortyeight/harness/pump_multi_hop_curve_differential.py',[]),('multihop-two-curve',R/'scripts/pump_tokenkeg_two_curve_differential.py',['--source-directory',str(P/'build/source/programs/pump'),'--build-report',str(P/'build/build-comparison.json')])]
state={}
def save():(P/'regression-state.json').write_text(json.dumps(state,indent=2)+'\n')
def run(job):
 name,script,extra=job;out=P/(name+('.json'if name=='multihop-native'else'.json.gz'));cmd=[sys.executable,str(W),'--receipt',str(P/(name+'.loader.json')),str(script),'--candidate',str(C),'--output',str(out),*extra];t=time.monotonic()
 with (P/(name+'.log')).open('w')as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 return name,{'returncode':r.returncode,'seconds':time.monotonic()-t,'command':cmd,'output':str(out)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
 for future in concurrent.futures.as_completed([pool.submit(run,j)for j in jobs]):
  name,row=future.result();state[name]=row;save();print(name,row['returncode'],flush=True)
assert all(x['returncode']==0 for x in state.values())
