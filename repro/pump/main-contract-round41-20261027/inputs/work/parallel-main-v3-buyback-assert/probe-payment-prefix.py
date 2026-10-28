"""Signed V3 Sell faults that distinguish payments before buyback validation."""
from pathlib import Path
import sys,inspect,json,gzip,hashlib,argparse,struct,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
from pump_diagnostic_audit import audit
source=inspect.getsource(h.run);old='ua=token_account(user.pubkey(),10**12)';assert source.count(old)==1;source=source.replace(old,"ua=token_account(user.pubkey(),c.get('user_quote_amount',10**12))");ns=dict(h.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);run=ns['run']
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
cases=[]
for bps in [10000,15000]:
 for fault in ['curve_lamports','user_lamports','token_credit']:
  cases.append((bps,fault))
cases.append((5000,'protocol_overflow'))
for bps,fault in cases:
 old=h.initial[h.curve]
 try:
  ac=old;data=bytearray(ac.data);lamports=ac.lamports
  if fault=='curve_lamports':lamports=1000
  if fault=='protocol_overflow':struct.pack_into('<Q',data,133,2**64-1)
  h.initial[h.curve]=h.f.Account(lamports,bytes(data),ac.owner)
  c={'name':f'{bps}-{fault}','operation':'sell_v3','reserve_in':h.base_in,'reserve_out':h.base_out,'amount':500000000,'max_cost':0,'token_quote':fault=='token_credit','replace':13,'user_lamports':2**64-1 if fault=='user_lamports'else 10**16,'fees':[95,30,bps]}
  if fault=='token_credit':c['quote_fees']=[95,30,bps];c['user_quote_amount']=2**64-1
  o=run(R/'evidence/original/pump/deployed.so',c);n=run(a.candidate,c)
 finally:h.initial[h.curve]=old
 assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]]
 invokes=lambda r:[x for x in r['logs']if re.match(r'Program \S+ invoke \[\d+\]',x)]
 rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'original_invocations':invokes(o),'candidate_invocations':invokes(n)});print(c['name'],o['error'],n['error'],invokes(o),diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'transformed_run_sha256':hashlib.sha256(source.encode()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};r['diagnostics']=audit({'payment_prefix':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));print('cases',len(rows),'mismatches',r['mismatches'])
