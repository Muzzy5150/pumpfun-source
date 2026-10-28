"""Signed V3 buyback failures that arise only after a first fill completes the curve."""
from pathlib import Path
import sys,inspect,json,gzip,hashlib,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
from pump_diagnostic_audit import audit
source=inspect.getsource(h.run);needle="    if 'real_base' in c:struct.pack_into('<Q',data,24,c['real_base'])";assert source.count(needle)==1;source=source.replace(needle,needle+"\n    if 'real_quote' in c:struct.pack_into('<Q',data,32,c['real_quote'])");ns=dict(h.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);run=ns['run']
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for op in ['buy_v3','buy_exact_quote_in_v3']:
 for token in [False,True]:
  for bps in [10001,15000]:
   c={'name':f'{op}-{token}-{bps}-post-buyback','operation':op,'reserve_in':h.base_in,'reserve_out':h.base_out,'real_base':1,'real_quote':10**9,'base_vault_amount':10**9+1,'amount':10**8+1 if op=='buy_v3' else 10**9,'max_cost':10**15 if op=='buy_v3' else 1,'trailing':[0],'token_quote':token,'replace':13,'user_lamports':10**16,'fees':[95,30,bps]}
   if token:c['quote_fees']=[95,30,bps]
   o=run(R/'evidence/original/pump/deployed.so',c);n=run(a.candidate,c);assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'transformed_run_sha256':hashlib.sha256(source.encode()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};r['diagnostics']=audit({'buyback_post':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));print(json.dumps({'count':len(rows),'mismatches':r['mismatches'],'diagnostics':len(r['diagnostics']['mismatches'])}))
