from pathlib import Path
import concurrent.futures,gzip,json,subprocess,sys,time
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;C=P/'build02/candidate.so';W=R/'work/parallel-main-loader-optimized/pump_with_captured_loader.py'
sys.path.insert(0,str(R/'work/parallel-main-v3-buyback-assert'));from audit_invocations import audit_invocations
V=R/'work/parallel-main-v3-fee-waiver';Q=R/'work/parallel-main-v3-post-ceil'
jobs=[('buy-v2',R/'scripts/pump_buy_v2_differential.py',[]),('v3-configured',R/'scripts/pump_v3_configured_fee_differential.py',[]),('v3-extensions',R/'scripts/pump_v3_token_extensions_differential.py',[]),('v3-continuation',R/'work/parallel-main-trading-contexts/probe_v3_continuation.py',['--require-match']),('v3-post-fees',R/'work/parallel-main-trading-contexts/probe_v3_post_fees.py',['--require-match']),('v3-native-buyback',R/'work/parallel-main-v3-user-constraints/probe_buyback.py',['--require-match']),('v3-token-buyback',R/'work/parallel-main-v3-user-constraints/probe_buyback_token.py',['--require-match']),('v3-crossing',V/'probe-waived-crossing.py',[]),('v3-matrix',V/'probe-crossing-matrix.py',[]),('price-divisible',Q/'probe.py',[]),('price-boundaries',Q/'probe-boundaries.py',[]),('v3-order',V/'probe-order.py',[]),('buyback54',R/'work/parallel-main-v3-buyback-assert/probe.py',[]),('buyback-order16',R/'work/parallel-main-v3-buyback-assert/probe-order.py',[]),('buyback-post8',R/'work/parallel-main-v3-buyback-assert/probe-post.py',[]),('buyback-prefix7',R/'work/parallel-main-v3-buyback-assert/probe-payment-prefix.py',[]),('buyback-protocol4',R/'work/parallel-main-v3-buyback-assert/probe-protocol-overflow.py',[]),('quote-order22',R/'work/parallel-main-v3-quote-validation-order/probe.py',[]),('cost-order8',R/'work/parallel-main-v3-accounting-boundary/probe-cost-order.py',[])]
jobs += [('owned-order48',P/'probe-owned-order.py',[]),('creator-rent108',R/'work/parallel-main-v2-creator-vault-rent/probe.py',[]),('payment-order64',R/'work/parallel-main-buy-native-recipient/probe-payment-order.py',[])]
state={}
def run(job):
 name,script,extra=job;out=P/(name+'02.json.gz');cmd=[sys.executable,str(W),'--receipt',str(P/(name+'02.loader.json')),str(script),'--candidate',str(C),'--output',str(out),*extra];t=time.monotonic()
 with (P/(name+'02.log')).open('w')as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 code=r.returncode;count=0
 if code==0 and out.exists():
  blob=out.read_bytes();report=json.loads(gzip.decompress(blob)if blob[:2]==b'\x1f\x8b'else blob);count=report.get('case_count',len(report.get('cases',[])))
  if report.get('mismatches')or report.get('diagnostics',{}).get('mismatches'):code=1
  audit=audit_invocations(report);(P/(name+'02.invocations.json')).write_text(json.dumps(audit,indent=2)+'\n')
  if audit['mismatches']:code=1
 return name,{'returncode':code,'process_returncode':r.returncode,'case_count':count,'seconds':time.monotonic()-t,'command':cmd,'output':str(out)}
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 for future in concurrent.futures.as_completed([pool.submit(run,j)for j in jobs]):
  name,row=future.result();state[name]=row;(P/'runtime-state02.json').write_text(json.dumps(state,indent=2)+'\n');print(name,row['returncode'],row['case_count'],flush=True)
if any(v['returncode']for v in state.values()):raise SystemExit(1)
