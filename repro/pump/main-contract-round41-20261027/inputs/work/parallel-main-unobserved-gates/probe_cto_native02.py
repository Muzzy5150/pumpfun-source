"""Correct native-quote precedence controls: preserve the harness's native mint accounts."""
from pathlib import Path
import sys,argparse,base64,gzip,hashlib,json
from solders.transaction import VersionedTransaction
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'scripts'),str(R/'work/parallel-main-loader-optimized')]
import pump_captured_loader as loader
loader.install()
import pump_admin_cto_differential as h
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for cashback,fee in [(True,None),(True,0),(True,1),(False,1)]:
 c={'name':f'native_cashback_{cashback}_fee_{fee}','curve_patches':[(82,'01'if cashback else'00')],'global_patches':[(1045,'01')]}
 if fee is not None:c['fee']=fee
 start=len(loader.LOADS);o=h.run(c);n=h.run(c,a.candidate)
 for result in [o,n]:assert all(VersionedTransaction.from_bytes(base64.b64decode(result['transaction_base64'])).verify_with_results())
 assert o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','before','after','events','inner','return']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loader.LOADS[start:]});print(json.dumps({'case':c['name'],'original':o['error'],'candidate':n['error'],'diff':diff}),flush=True)
r={'case_count':len(rows),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'suites':{'native_cto':rows},'diagnostics':audit({'native_cto':rows})};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0))
