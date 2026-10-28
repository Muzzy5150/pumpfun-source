"""Signed V3 sell fee-tier selection when mint supply differs from stored curve supply."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,struct
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
mint_key=h.f.ixs[-1].accounts[1].pubkey
low=struct.pack('<QQQ',0,10,10);high=struct.pack('<QQQ',0,1000,200)
tiers=struct.pack('<I',2)+int(0).to_bytes(16,'little')+low+int(10**6).to_bytes(16,'little')+high
for token in [False,True]:
 for mayhem in [False,True]:
  for mint_supply,curve_supply in [(10**15,10**15),(10**9,10**15),(10**15,10**9),(10**9,10**9)]:
   old={key:h.initial[key]for key in [mint_key,h.curve,h.fee_key]}
   try:
    ac=old[mint_key];d=bytearray(ac.data);struct.pack_into('<Q',d,36,mint_supply);h.initial[mint_key]=h.f.Account(ac.lamports,bytes(d),ac.owner)
    ac=old[h.curve];d=bytearray(ac.data);struct.pack_into('<Q',d,40,curve_supply);h.initial[h.curve]=h.f.Account(ac.lamports,bytes(d),ac.owner)
    ac=old[h.fee_key];d=ac.data[:41]+low+tiers+tiers+low;h.initial[h.fee_key]=h.f.Account(ac.lamports,d.ljust(len(ac.data),b'\0'),ac.owner)
    c={'name':f'token-{token}-mayhem-{mayhem}-mint-{mint_supply}-stored-{curve_supply}','operation':'sell_v3','reserve_in':h.base_in,'reserve_out':h.base_out,'amount':500000000,'max_cost':0,'token_quote':token,'replace':13,'user_lamports':10**16,'flags':[81]if mayhem else[]}
    o=h.run(R/'evidence/original/pump/deployed.so',c);n=h.run(a.candidate,c)
   finally:h.initial.update(old)
   assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64']
   diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]]
   rows.append({'case':c,'mint_supply':mint_supply,'curve_supply':curve_supply,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};r['diagnostics']=audit({'sell_supply':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));print(json.dumps({'count':len(rows),'mismatches':r['mismatches'],'diagnostics':len(r['diagnostics']['mismatches'])}))
