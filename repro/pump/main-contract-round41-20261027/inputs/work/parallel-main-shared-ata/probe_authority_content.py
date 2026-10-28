from pathlib import Path
import argparse,base64,gzip,hashlib,json,sys
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'))
import buy_fixture as b
import sell_fixture as s
import pump_fee_sweep_differential as w
from pump_diagnostic_audit import messages
from solders.transaction import VersionedTransaction
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[Path(__file__),Path(b.__file__),Path(s.__file__),Path(w.__file__),R/'scripts/pump_trade_fixture.py',R/'scripts/pump_diagnostic_audit.py',a.candidate,R/'evidence/original/pump/deployed.so'];bound={str(p):sha(p)for p in paths};rows=[]
roles=['associated_quote_bonding_curve','associated_quote_user','associated_creator_vault','associated_user_volume_accumulator','associated_quote_fee_recipient','associated_quote_buyback_fee_recipient']
for family,h in [('buy',b),('sell',s)]:
 for token22 in [False,True]:
  for role in roles:
   for value in [0,199]:
    c={'name':f'{family}_{token22}_{role}_authority_{value}','token_quote':True,'token22':token22,'account_mutations':{role:{'bytes':[(32+i,value)for i in range(32)]}}}
    x=h.run(c);y=h.run(c,a.candidate);tx=VersionedTransaction.from_bytes(base64.b64decode(x['transaction_base64']));assert all(tx.verify_with_results())and x['transaction_base64']==y['transaction_base64']
    diff=[k for k in ['error','accounts','events','inner','return_data']if x[k]!=y[k]]
    if messages(x['logs'])!=messages(y['logs']):diff.append('diagnostics')
    rows.append({'case':c,'original':x,'candidate':y,'different_fields':diff,'verified_signatures':len(tx.signatures)});print(c['name'],x['error'],y['error'],diff,flush=True)
for token22 in [False,True]:
 for role in ['associated_quote_bonding_curve','associated_quote_recipient']:
  for value in [0,199]:
   c={'name':f'sweep_{token22}_{role}_authority_{value}','quote':str(w.STABLE),'token22':token22,'patch':{role:{'bytes':[(32,(bytes([value])*32).hex())]}}}
   x=w.run(c);y=w.run(c,a.candidate);tx=VersionedTransaction.from_bytes(base64.b64decode(x['transaction_base64']));assert all(tx.verify_with_results())and x['transaction_base64']==y['transaction_base64']
   diff=[k for k in ['error','before','after']if x[k]!=y[k]]
   for k in ['return_data','inner_instructions']:
    if x['metadata'][k]!=y['metadata'][k]:diff.append(k)
   if messages(x['logs'])!=messages(y['logs']):diff.append('diagnostics')
   rows.append({'case':c,'original':x,'candidate':y,'different_fields':diff,'verified_signatures':len(tx.signatures)});print(c['name'],x['error'],y['error'],diff,flush=True)
assert bound=={str(p):sha(p)for p in paths}
out={'scope':'Token-account internal authority content, separate from AccountInfo program owner: identical signed transactions and captured dependencies.','candidate_sha256':sha(a.candidate),'input_sha256':bound,'case_count':len(rows),'cases':rows,'mismatches':[r['case']['name']for r in rows if r['different_fields']]}
a.output.write_bytes(gzip.compress(json.dumps(out,separators=(',',':')).encode(),mtime=0));print('DONE',len(rows),len(out['mismatches']))
