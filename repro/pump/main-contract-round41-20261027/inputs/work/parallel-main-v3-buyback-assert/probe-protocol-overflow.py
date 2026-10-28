"""Signed V3 Sell accrued-protocol overflow before transfer controls."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,struct,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for token in [False,True]:
 for bps in [5000,10000]:
  old=h.initial[h.curve]
  try:
   d=bytearray(old.data);struct.pack_into('<Q',d,133,2**64-1);h.initial[h.curve]=h.f.Account(old.lamports,bytes(d),old.owner)
   c={'name':f'{token}-{bps}-protocol-max','operation':'sell_v3','reserve_in':h.base_in,'reserve_out':h.base_out,'amount':500000000,'max_cost':0,'token_quote':token,'replace':13,'user_lamports':10**16,'fees':[95,30,bps]}
   if token:c['quote_fees']=[95,30,bps]
   o=h.run(R/'evidence/original/pump/deployed.so',c);n=h.run(a.candidate,c)
  finally:h.initial[h.curve]=old
  diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];invoke=lambda r:[x for x in r['logs']if re.match(r'Program \S+ invoke \[\d+\]',x)];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'original_invocations':invoke(o),'candidate_invocations':invoke(n)});print(c['name'],o['error'],n['error'],invoke(o),diff)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};r['diagnostics']=audit({'protocol_overflow':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0))
