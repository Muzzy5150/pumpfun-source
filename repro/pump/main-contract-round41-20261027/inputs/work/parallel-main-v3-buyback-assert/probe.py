"""Signed V3 buyback quotient/remainder boundaries and mayhem/whitelist controls."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for op in ['buy_v3','buy_exact_quote_in_v3','sell_v3']:
 for token in [False,True]:
  for bps in [10000,15000,2**64-1]:
   for mode in ['normal','mayhem','waived']:
    old=h.initial[h.global_key]
    try:
     if mode=='waived':
      d=bytearray(old.data);d[451:483]=bytes(h.user.pubkey());h.initial[h.global_key]=h.f.Account(old.lamports,bytes(d),old.owner)
     c={'name':f'{op}-token-{token}-bps-{bps}-{mode}','operation':op,'reserve_in':h.base_in,'reserve_out':h.base_out,'amount':500000000 if op=='sell_v3'else 10**9,'max_cost':0 if op=='sell_v3'else 10**12 if op=='buy_v3'else 1,'token_quote':token,'replace':13,'user_lamports':10**16,'fees':[95,30,bps],'flags':[81]if mode=='mayhem'else[]}
     if token:c['quote_fees']=[95,30,bps]
     o=h.run(R/'evidence/original/pump/deployed.so',c);n=h.run(a.candidate,c)
    finally:h.initial[h.global_key]=old
    assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};r['diagnostics']=audit({'buyback':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));print(json.dumps({'count':len(rows),'mismatches':r['mismatches'],'diagnostics':len(r['diagnostics']['mismatches'])}))
