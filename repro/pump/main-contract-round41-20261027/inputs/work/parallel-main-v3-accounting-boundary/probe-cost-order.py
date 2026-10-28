"""Signed V3 initial-cost overflow versus post-pool validation ordering."""
from pathlib import Path
import sys,argparse,json,gzip,hashlib
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for token in [False,True]:
 for crossing in [False,True]:
  for rate in [0,9300000000000000000]:
   c={'name':f'token-{token}-crossing-{crossing}-bps-{rate}','operation':'buy_v3','reserve_in':10**9,'reserve_out':10**7,'real_base':1000000,'base_vault_amount':1000000,'amount':1000001 if crossing else 1000000,'max_cost':2**64-1,'trailing':[0],'token_quote':token,'replace':13,'user_lamports':10**16,'fees':[rate,rate,0]}
   if token:c['quote_fees']=[rate,rate,0]
   o=h.run(R/'evidence/original/pump/deployed.so',c);n=h.run(a.candidate,c);assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,x in enumerate(rows)if x['different_fields']]};r['diagnostics']=audit({'cost-order':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0))
