"""Signed V3 malformed quote-fee data combined with business failures."""
from pathlib import Path
import sys,json,gzip,argparse,hashlib
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_token_extensions_differential as h
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[];cases=[]
for op in ['buy_v3','buy_exact_quote_in_v3','sell_v3']:
 for malformed in [False,True]:
  for fault in ['none','empty_tiers','zero']:
   c={'name':f'{op}-{malformed}-{fault}','operation':op,'token_quote':True,'quote2022':True,'replace':13,'reserve_in':h.base_in,'reserve_out':h.base_out,'user_lamports':10**16,'extension':True,'bps':100,'amount':10**9 if op!='sell_v3'else 500000000,'max_cost':10**12 if op=='buy_v3'else 0 if op=='sell_v3'else 1}
   if malformed:c['mint_length']=170
   if fault=='empty_tiers':c['mutation']='empty_tiers'
   if fault=='zero':c['amount']=0
   cases.append(c)
for malformed in [False,True]:
 for bps in [0,9300000000000000000]:
  c={'name':f'buy-crossing-{malformed}-{bps}','operation':'buy_v3','token_quote':True,'quote2022':True,'replace':13,'reserve_in':10**9,'reserve_out':10**7,'real_base':1000000,'base_vault_amount':1000000,'amount':1000001,'max_cost':2**64-1,'user_lamports':10**16,'extension':True,'bps':100,'quote_fees':[bps,bps,0]}
  if malformed:c['mint_length']=170
  cases.append(c)
for c in cases:
 o=h.run(R/'evidence/original/pump/deployed.so',c);n=h.run(a.candidate,c);assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,x in enumerate(rows)if x['different_fields']]};r['diagnostics']=audit({'quote-order':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0))
