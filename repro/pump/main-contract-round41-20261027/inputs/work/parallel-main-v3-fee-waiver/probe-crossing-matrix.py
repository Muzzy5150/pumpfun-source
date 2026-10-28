"""Signed V3 fee-waived post-completion fills with explicit real reserves."""
from pathlib import Path
import argparse,base64,gzip,hashlib,inspect,json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as v
from pump_diagnostic_audit import audit
source=inspect.getsource(v.run);needle="    if 'real_base' in c:struct.pack_into('<Q',data,24,c['real_base'])";assert source.count(needle)==1
source=source.replace(needle,needle+"\n    if 'real_quote' in c:struct.pack_into('<Q',data,32,c['real_quote'])")
namespace=dict(v.__dict__);exec(compile(source,str(Path(__file__)), 'exec'),namespace);inner=namespace['run']
def run(binary,c):
 old=v.initial[v.global_key]
 try:
  data=bytearray(old.data);data[451:483]=bytes(v.user.pubkey());v.initial[v.global_key]=v.f.Account(old.lamports,bytes(data),old.owner)
  return inner(binary,c)
 finally:v.initial[v.global_key]=old
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for op in ['buy_v3','buy_exact_quote_in_v3']:
 for token in [False,True]:
  for partial in [False,True]:
   for minimum in ([10**15]if op=='buy_v3'else[1,1000001]):
    amount=2000000 if op=='buy_v3'else 10**6
    c={'operation':op,'reserve_in':v.base_in,'reserve_out':v.base_out,'user_lamports':10**16,'real_base':1000000,'real_quote':10**9,'token_quote':token,'replace':13,'flags':[],'trailing':[int(partial)],'amount':amount,'max_cost':minimum}
    x=run(R/'evidence/original/pump/deployed.so',c);y=run(a.candidate,c);fields=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if x[k]!=y[k]];rows.append({'case':c,'original':x,'candidate':y,'different_fields':fields});print(op,token,partial,minimum,x['error'],fields,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'transformed_run_sha256':hashlib.sha256(source.encode()).hexdigest(),'case_count':len(rows),'mismatches':[i for i,x in enumerate(rows)if x['different_fields']],'cases':rows};r['diagnostics']=audit({'waived_crossing':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));print(len(rows),len(r['mismatches']),len(r['diagnostics']['mismatches']));# Research control: mismatches retained as evidence.
