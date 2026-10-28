from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'parallel-main-v3-buyback-assert'))
from audit_invocations import audit_invocations
import concurrent.futures,subprocess,sys,json,time,gzip
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;C=P/'build02/candidate.so';W=R/'work/parallel-main-loader-optimized/pump_with_captured_loader.py';V=R/'work/parallel-main-v3-fee-waiver';Q=R/'work/parallel-main-v3-post-ceil'
jobs=[('v3-focused',R/'work/parallel-main-global-fee-waiver/probe-v3.py',[],False,False),('v3-order',V/'probe-order.py',[],False,False),('v3-configured',R/'scripts/pump_v3_configured_fee_differential.py',[],False,False),('v3-extensions',R/'scripts/pump_v3_token_extensions_differential.py',[],False,False),('v3-continuation',R/'work/parallel-main-trading-contexts/probe_v3_continuation.py',['--require-match'],False,False),('v3-post-fees',R/'work/parallel-main-trading-contexts/probe_v3_post_fees.py',['--require-match'],False,False),('v3-native-buyback',R/'work/parallel-main-v3-user-constraints/probe_buyback.py',['--require-match'],False,False),('v3-token-buyback',R/'work/parallel-main-v3-user-constraints/probe_buyback_token.py',['--require-match'],False,False),('v3-crossing',V/'probe-waived-crossing.py',[],False,False),('v3-matrix',V/'probe-crossing-matrix.py',[],False,False),('price-divisible',Q/'probe.py',[],False,False),('price-boundaries',Q/'probe-boundaries.py',[],False,False),('v3-precedence',R/'work/parallel-main-v3-helpers/probe_precedence_extended.py',['--require-match'],False,False),('multihop-native',R/'repro/pump/native-curve-partial-fortyeight/harness/pump_multi_hop_curve_differential.py',[],False,True),('multihop-two-curve',R/'scripts/pump_tokenkeg_two_curve_differential.py',['--source-directory',str(P/'build02/source/programs/pump'),'--build-report',str(P/'build02/build-comparison.json')],False,False),('sell-v2',R/'scripts/pump_sell_v2_differential.py',[],False,True),('sell-v2-guards',R/'work/parallel-main-sell-v2-buyback/probe-expanded.py',[],True,False),('sell-v2-atas',R/'work/parallel-main-sell-v2-buyback/probe-atas.py',[],True,False),('sell-v2-prepare',R/'work/parallel-main-sell-v2-buyback/probe-prepare.py',[],True,False),('v3-supply',R/'work/parallel-main-v3-net-budget/probe-sell-supply.py',[],False,False),('v3-zero-reserve',R/'work/parallel-main-v3-sell-supply/probe-zero-reserve.py',[],False,False)]
jobs[0:0]=[('buyback54',R/'work/parallel-main-v3-buyback-assert/probe.py',[],False,False),('buyback-order16',R/'work/parallel-main-v3-buyback-assert/probe-order.py',[],False,False),('buyback-post8',R/'work/parallel-main-v3-buyback-assert/probe-post.py',[],False,False),('buyback-prefix7',R/'work/parallel-main-v3-buyback-assert/probe-payment-prefix.py',[],False,False),('buyback-protocol4',R/'work/parallel-main-v3-buyback-assert/probe-protocol-overflow.py',[],False,False)]
state={}
def save():(P/'regression-state.json').write_text(json.dumps(state,indent=2)+'\n')
def run(job):
 name,script,extra,direct,plain=job;out=P/(name+('.json'if plain else'.json.gz'));cmd=[sys.executable]+([]if direct else[str(W),'--receipt',str(P/(name+'.loader.json'))])+[str(script),'--candidate',str(C),'--output',str(out),*extra];t=time.monotonic()
 with (P/(name+'.log')).open('w')as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 code=r.returncode
 if code==0 and out.exists():
  blob=out.read_bytes();report=json.loads(gzip.decompress(blob) if blob[:2]==b'\x1f\x8b' else blob)
  if report.get('mismatches') or report.get('diagnostics',{}).get('mismatches'):code=1
  if name.startswith('buyback'):
   call_audit=audit_invocations(report);(P/(name+'-invocations.json')).write_text(json.dumps(call_audit,indent=2)+'\n')
   if call_audit['mismatches']:code=1
 return name,{'returncode':code,'process_returncode':r.returncode,'seconds':time.monotonic()-t,'command':cmd,'output':str(out),'direct_captured_loader':direct}
for phase in [jobs[:5],jobs[5:]]:
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
  for future in concurrent.futures.as_completed([pool.submit(run,j)for j in phase]):
   name,row=future.result();state[name]=row;save();print(name,row['returncode'],flush=True)
 if any(x['returncode']!=0 for x in state.values()):raise SystemExit(1)
