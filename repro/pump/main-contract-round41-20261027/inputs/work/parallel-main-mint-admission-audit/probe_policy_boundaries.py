from pathlib import Path
import argparse,base64,gzip,hashlib,json,re,sys
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'))
import pump_create_quote_differential as h
from pump_diagnostic_audit import messages
from solders.transaction import VersionedTransaction
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();cases=[]
def add(name,ext):cases.append({'case':name,'instruction':'create_v2','quote':True,'quote_token22':True,'quote_extensions':[(t,d.hex())for t,d in ext]})
for size in [0,1,32,107,108,109,128]:add(f'transfer-fee-size-{size}',[(1,bytes(size))])
for size in [0,1,2,8]:
 for value in ([0]if not size else[0,1,2,255]):add(f'default-state-{size}-{value}',[(6,bytes([value])*size)])
for size in [0,1,32,63,64,65,96]:add(f'transfer-hook-size-{size}',[(14,bytes(size))])
for at in [0,1,31,32,33,63,64,65,95]:
 d=bytearray(96);d[at]=199;add(f'transfer-hook-nonzero-{at}',[(14,bytes(d))])
for kind in [4,12,16,18,19,25,26]:
 for size in [0,1,64]:add(f'allowed-{kind}-{size}',[(kind,bytes(size))])
for kind in [2,3,5,7,8,9,10,11,13,15,17,20,21,22,23,24,27,28,63,64,255,65535]:
 for size in [0,1]:add(f'rejected-{kind}-{size}',[(kind,bytes(size))])
for tail in [[(0,b''),(65535,b'')],[(18,b''),(0,b''),(18,b'')],[(14,bytes(64)),(0,b''),(14,bytes(64))],[(18,b''),(19,b''),(18,b'')],[(18,b''),(4,b'')],[(4,b''),(18,b'')]]:add('sequence-'+str(len(cases)),tail)
inputs=[Path(__file__),Path(h.__file__),R/'scripts/pump_diagnostic_audit.py',R/'evidence/original/pump/deployed.so',a.candidate];bound={str(p):sha(p)for p in inputs};rows=[]
for c in cases:
 x=h.run(c);y=h.run(c,a.candidate);tx=VersionedTransaction.from_bytes(base64.b64decode(x['transaction_base64']));assert all(tx.verify_with_results())and x['transaction_base64']==y['transaction_base64']
 diff=[k for k in ['error','before','after','events','inner','return']if x[k]!=y[k]]
 if messages(x['logs'])!=messages(y['logs']):diff.append('diagnostics')
 rows.append({'case':c,'original':x,'candidate':y,'different_fields':diff,'verified_signatures':len(tx.signatures)});print(c['case'],x['error'],y['error'],diff,flush=True)
assert bound=={str(p):sha(p)for p in inputs};out={'scope':'Actual CreateV2 main caller with true token-extension policy; normally signed transactions, unchanged captured dependencies. Does not claim a reachable false-policy caller.','candidate_sha256':sha(a.candidate),'input_sha256':bound,'case_count':len(rows),'cases':rows,'mismatches':[r['case']['case']for r in rows if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(out,separators=(',',':')).encode(),mtime=0));print('DONE',len(rows),len(out['mismatches']))
