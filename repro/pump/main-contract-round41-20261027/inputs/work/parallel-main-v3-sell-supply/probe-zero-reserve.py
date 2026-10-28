"""Signed V3 sell zero virtual-token reserve and zero-input precedence controls."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for token in [False,True]:
 for amount in [0,500000000]:
  c={'name':f'token-{token}-zero-reserve-amount-{amount}','operation':'sell_v3','reserve_in':0,'reserve_out':h.base_out,'amount':amount,'max_cost':0,'token_quote':token,'replace':13,'user_lamports':10**16}
  o=h.run(R/'evidence/original/pump/deployed.so',c);n=h.run(a.candidate,c);assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};r['diagnostics']=audit({'zero_reserve':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));print(json.dumps({'count':len(rows),'mismatches':r['mismatches'],'diagnostics':len(r['diagnostics']['mismatches'])}))
