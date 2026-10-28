"""Signed V3 exact-input net-budget boundary matrix, original versus frozen candidate."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
patterns=[(0,0,1),(0,0,2),(1,1,2),(1,1,3),(95,30,1),(95,30,2),(95,30,3),(95,30,80),(95,30,81),(333,777,9),(333,777,10),(333,777,11),(5000,5000,2),(5000,5000,3),(10000,10000,3),(10000,10000,4),(2**64-1,0,1),(2**64-1,1,1),(2**64-1,1,2),(2**63,2**63,1),(2**63,2**63-1,1),(2**63,2**63-1,2),(2**64-1,2**64-1,1),(2**64-1,2**64-1,2)]
for token in [False,True]:
 for zero in [False,True]:
  for pb,cb,spend in patterns:
   c={'name':f'token-{token}-creatorzero-{zero}-{pb}-{cb}-{spend}','operation':'buy_exact_quote_in_v3','reserve_in':h.base_in,'reserve_out':h.base_out,'amount':spend,'max_cost':1,'token_quote':token,'replace':13,'user_lamports':10**16,'fees':[pb,cb,0],'mutation':'creator_zero'if zero else'none'}
   if token:c['quote_fees']=[pb,cb,0]
   o=h.run(R/'evidence/original/pump/deployed.so',c);n=h.run(a.candidate,c)
   assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64']
   diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]]
   row={'case':c,'original':o,'candidate':n,'different_fields':diff};rows.append(row)
   print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};r['diagnostics']=audit({'budget':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));print(json.dumps({'count':len(rows),'mismatches':r['mismatches'],'diagnostics':len(r['diagnostics']['mismatches'])}))
