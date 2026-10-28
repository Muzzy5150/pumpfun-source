from pathlib import Path
import argparse,base64,gzip,hashlib,json,re,sys
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'))
import quote_key_fixture as h
from pump_diagnostic_audit import messages
from solders.transaction import VersionedTransaction
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();cases=[]
def add(name,ext):cases.append({'case':name,'instruction':'create_v2','quote':True,'quote_token22':True,'quote_extensions':[(t,d.hex())for t,d in ext]})
pump='pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn'
for special in [False,True]:
 for token22 in [False,True]:
  for label,ext,mut in [('base',[],None),('metadata',[(18,bytes(64))],None),('group-pointer',[(20,bytes(64))],None),('member-pointer',[(22,bytes(64))],None),('unknown',[(29,b'')],None),('short-fee',[(1,bytes(107))],None),('padding',[(18,bytes(64))],{'patches':[(82,'01')]}),('duplicate',[(18,bytes(64)),(18,bytes(64))],None)]:
   c={'case':f'{special}-{token22}-{label}','instruction':'create_v2','quote':True,'quote_token22':token22,'quote_extensions':[(t,d.hex())for t,d in ext]}
   if special:c['quote_key']=pump
   if mut:c['mutations']={'quote_mint':mut}
   cases.append(c)
inputs=[Path(__file__),Path(h.__file__),R/'scripts/pump_diagnostic_audit.py',R/'evidence/original/pump/deployed.so',a.candidate];bound={str(p):sha(p)for p in inputs};rows=[]
for c in cases:
 x=h.run(c);y=h.run(c,a.candidate);tx=VersionedTransaction.from_bytes(base64.b64decode(x['transaction_base64']));assert all(tx.verify_with_results())and x['transaction_base64']==y['transaction_base64']
 diff=[k for k in ['error','before','after','events','inner','return']if x[k]!=y[k]]
 if messages(x['logs'])!=messages(y['logs']):diff.append('diagnostics')
 rows.append({'case':c,'original':x,'candidate':y,'different_fields':diff,'verified_signatures':len(tx.signatures)});print(c['case'],x['error'],y['error'],diff,flush=True)
assert bound=={str(p):sha(p)for p in inputs};out={'scope':'Actual CreateV2 scanner invocation gate: token program versus observed literal quote-mint bypass. Normally signed identical transactions and captured dependencies.','candidate_sha256':sha(a.candidate),'input_sha256':bound,'case_count':len(rows),'cases':rows,'mismatches':[r['case']['case']for r in rows if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(out,separators=(',',':')).encode(),mtime=0));print('DONE',len(rows),len(out['mismatches']))
