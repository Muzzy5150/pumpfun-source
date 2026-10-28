from pathlib import Path
import argparse,base64,gzip,hashlib,json,re,sys
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'))
import quote_key_fixture as h
from pump_diagnostic_audit import messages
from solders.transaction import VersionedTransaction
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();cases=[]
def add(name,ext):cases.append({'case':name,'instruction':'create_v2','quote':True,'quote_token22':True,'quote_extensions':[(t,d.hex())for t,d in ext]})
defs=W/'incremental-cases.json';cases=json.loads(defs.read_text())
inputs=[defs,Path(__file__),Path(h.__file__),R/'scripts/pump_diagnostic_audit.py',R/'evidence/original/pump/deployed.so',a.candidate];bound={str(p):sha(p)for p in inputs};rows=[]
for c in cases:
 x=h.run(c);y=h.run(c,a.candidate);tx=VersionedTransaction.from_bytes(base64.b64decode(x['transaction_base64']));assert all(tx.verify_with_results())and x['transaction_base64']==y['transaction_base64']
 diff=[k for k in ['error','before','after','events','inner','return']if x[k]!=y[k]]
 if messages(x['logs'])!=messages(y['logs']):diff.append('diagnostics')
 rows.append({'case':c,'original':x,'candidate':y,'different_fields':diff,'verified_signatures':len(tx.signatures)});print(c['case'],x['error'],y['error'],diff,flush=True)
assert bound=={str(p):sha(p)for p in inputs};out={'scope':'Incremental CreateV2 quote-admission cases after exact input deduplication; normal signed transactions and captured dependencies.','candidate_sha256':sha(a.candidate),'input_sha256':bound,'case_count':len(rows),'cases':rows,'mismatches':[r['case']['case']for r in rows if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(out,separators=(',',':')).encode(),mtime=0));print('DONE',len(rows),len(out['mismatches']))
