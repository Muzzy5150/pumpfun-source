from pathlib import Path
import sys,json,gzip,subprocess,hashlib
P=Path(__file__).resolve().parent;R=P.parents[1];Q=R/'work/parallel-main-v3-buyback-assert';outdir=P/'runs04';outdir.mkdir();sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(Q));from pump_diagnostic_audit import audit;from audit_invocations import audit_invocations
suites={}
for name,script in [('basic','probe.py'),('order','probe-order.py'),('post','probe-post.py'),('prefix','probe-payment-prefix.py'),('protocol','probe-protocol-overflow.py')]:
 out=outdir/(name+'.json.gz');cmd=[sys.executable,str(R/'work/parallel-main-loader-optimized/pump_with_captured_loader.py'),'--receipt',str(outdir/(name+'.loader.json')),str(Q/script),'--candidate',str(P/'build04/candidate.so'),'--output',str(out)]
 with(outdir/(name+'.log')).open('w')as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(name,r.returncode);d=json.loads(gzip.decompress(out.read_bytes()));assert not d['mismatches'];assert not audit_invocations(d)['mismatches'];suites[name]=d
report=audit(suites);assert not report['mismatches'];assert sum(x['case_count']for x in suites.values())==89
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();result={'source':'source04','source_sha256':sha(P/'source04/src/trade_v3.rs'),'candidate_sha256':sha(P/'build04/candidate.so'),'unstripped_sha256':sha(P/'build04/unstripped.so'),'focused_cases':89,'diagnostic_mismatches':0,'invocation_mismatches':0,'original_helper_bytes':2120,'candidate_helper_bytes':2032,'different_slots':252,'normalized_windows':708,'raw_windows':123,'status':'Unpromoted ABI control: u8 restores masking but no new complete window; same known cost-order gap left unchanged.'};(P/'RESULT04.json').write_text(json.dumps(result,indent=2)+'\n');(P/'diagnostics04.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(result,indent=2))
