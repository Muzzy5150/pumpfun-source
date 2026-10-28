"""Signed V3 continuation fee tiers around pre- and post-first-fill market cap."""
from pathlib import Path
import inspect,sys,json,gzip,hashlib,argparse,struct,base64
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
from pump_diagnostic_audit import audit
source=inspect.getsource(h.run);needle="    if 'real_base' in c:struct.pack_into('<Q',data,24,c['real_base'])";assert source.count(needle)==1;source=source.replace(needle,needle+"\n    if 'real_quote' in c:struct.pack_into('<Q',data,32,c['real_quote'])")
ns=dict(h.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);run=ns['run']
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
supply=struct.unpack_from('<Q',h.initial[h.f.ixs[-1].accounts[1].pubkey].data,36)[0];real_base=1000000;before=supply*h.base_out//h.base_in;first_quote=real_base*h.base_out//(h.base_in-real_base)+1;after=supply*(h.base_out+first_quote)//(h.base_in-real_base)
def fees(p,c):return struct.pack('<QQQ',0,p,c)
for token in [False,True]:
 for op in ['buy_v3','buy_exact_quote_in_v3']:
  for threshold in [before,before+1,after+1]:
   old=h.initial[h.fee_key]
   try:
    tiers=struct.pack('<I',2)+bytes(16)+fees(95,30)+threshold.to_bytes(16,'little')+fees(1900,600)
    data=old.data[:41]+fees(95,30)+tiers+tiers+fees(95,30);h.initial[h.fee_key]=h.f.Account(old.lamports,data.ljust(4352,b'\0'),old.owner)
    c={'name':f'{op}-token-{token}-threshold-{threshold}','operation':op,'reserve_in':h.base_in,'reserve_out':h.base_out,'real_base':real_base,'real_quote':10**9,'base_vault_amount':10**9+real_base,'amount':2*real_base if op=='buy_v3'else 10**6,'max_cost':10**15 if op=='buy_v3'else 1,'trailing':[0],'token_quote':token,'replace':13,'user_lamports':10**16}
    o=run(R/'evidence/original/pump/deployed.so',c);n=run(a.candidate,c)
   finally:h.initial[h.fee_key]=old
   assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'market_cap_before':before,'computed_after_first_fill':after,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'transformed_run_sha256':hashlib.sha256(source.encode()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};r['diagnostics']=audit({'continuation_tiers':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));print(json.dumps({'count':len(rows),'mismatches':r['mismatches'],'diagnostics':len(r['diagnostics']['mismatches'])}))
