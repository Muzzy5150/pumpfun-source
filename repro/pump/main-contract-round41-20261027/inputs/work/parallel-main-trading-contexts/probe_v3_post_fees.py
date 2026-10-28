"""Signed post-completion ordinary-buy fee rounding and attribution probes."""
from pathlib import Path
import argparse,base64,gzip,hashlib,inspect,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import pump_v3_configured_fee_differential as v
from pump_diagnostic_audit import audit
source=inspect.getsource(v.run);needle="    if 'real_base' in c:struct.pack_into('<Q',data,24,c['real_base'])";assert source.count(needle)==1
source=source.replace(needle,needle+"\n    if 'real_quote' in c:struct.pack_into('<Q',data,32,c['real_quote'])")
namespace=dict(v.__dict__);exec(compile(source,str(Path(__file__)), 'exec'),namespace);run=namespace['run']
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-match',action='store_true');a=p.parse_args();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();original=ROOT/'evidence/original/pump/deployed.so';inputs={str(Path(p).resolve()):sha(p)for p in [__file__,v.__file__,v.f.__file__,a.candidate,original]};rows=[];cases=[]
for token in [False,True]:
 for fees in [[0,0,0],[1,1,1],[95,30,5000],[333,777,2500],[10000,10000,10000]]:
  for zero_creator in [False,True]:
   for holder in [False,True]:
    for amount in [1000001,2000000]:
     c={'token_quote':token,'fees':fees,'flags':[124]if holder else[],'mutation':'creator_zero'if zero_creator else'none','trailing':[0],'amount':amount,'max_cost':10**15}
     if token:c['quote_fees']=fees
     cases.append(c)
for i,c in enumerate(cases):
 c={'operation':'buy_v3','reserve_in':v.base_in,'reserve_out':v.base_out,'user_lamports':10**16,'real_base':1000000,'real_quote':10**9,'replace':13,**c}
 x=run(original,c);y=run(a.candidate,c);fields=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if x[k]!=y[k]];rows.append({'case':c,'original':x,'candidate':y,'different_fields':fields});print(i,c['token_quote'],c.get('flags',[]),c['trailing'],c['amount'],c['max_cost'],fields,flush=True)
r={'scope':__doc__,'input_sha256':inputs,'transformed_run_sha256':hashlib.sha256(source.encode()).hexdigest(),'case_count':len(rows),'mismatches':[i for i,x in enumerate(rows)if x['different_fields']],'cases':rows};r['diagnostics']=audit({'v3_continuation':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));assert inputs=={p:sha(p)for p in inputs};print(len(rows),len(r['mismatches']),len(r['diagnostics']['mismatches']));
if a.require_match:assert not r['mismatches'] and not r['diagnostics']['mismatches']
