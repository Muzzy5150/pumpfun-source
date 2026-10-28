from pathlib import Path
import sys,json,gzip,subprocess,concurrent.futures,hashlib
P=Path(__file__).resolve().parent;R=P.parents[1];Q=R/'work/parallel-main-v3-buyback-assert';sys.path.insert(0,str(Q));sys.path.insert(0,str(R/'scripts'))
from audit_invocations import audit_invocations
from pump_diagnostic_audit import audit
jobs=[('cost-order8',R/'work/parallel-main-v3-accounting-boundary/probe-cost-order.py'),('buyback54',Q/'probe.py'),('buyback-order16',Q/'probe-order.py'),('buyback-post8',Q/'probe-post.py'),('buyback-prefix7',Q/'probe-payment-prefix.py'),('buyback-protocol4',Q/'probe-protocol-overflow.py')]
def run(job):
 n,s=job;out=P/(n+'.json.gz');cmd=[sys.executable,str(R/'work/parallel-main-loader-optimized/pump_with_captured_loader.py'),'--receipt',str(P/(n+'.loader.json')),str(s),'--candidate',str(P/'build01/candidate.so'),'--output',str(out)]
 with(P/(n+'.log')).open('w')as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(n,r.returncode)
 d=json.loads(gzip.decompress(out.read_bytes()));assert not d.get('mismatches'),(n,d.get('mismatches'));assert not audit_invocations(d)['mismatches'],n
 return n,d
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:suites=dict(pool.map(run,jobs))
diag=audit(suites);assert not diag['mismatches'];assert sum(d['case_count']for d in suites.values())==97
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
result={'source_sha256':sha(P/'source01/src/trade_v3.rs'),'candidate_sha256':sha(P/'build01/candidate.so'),'unstripped_sha256':sha(P/'build01/unstripped.so'),'focused_cases':97,'diagnostic_mismatches':0,'invocation_mismatches':0,'case_counts':{k:d['case_count']for k,d in suites.items()},'source':'source01','change':'Move initial total-cost sum after post-pool validation and buyback assertions; retains entire accepted b499 V3 buyback correction.','base':'../parallel-main-v3-buyback-assert/source02','round21_counterexample':'round21-before.json.gz','patch':'cost-order.patch'}
(P/'FOCUSED-RESULT.json').write_text(json.dumps(result,indent=2)+'\n');(P/'diagnostics.json').write_text(json.dumps(diag,indent=2)+'\n');print(json.dumps(result,indent=2))
