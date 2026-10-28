"""Signed exact-divisibility probes for V3 post-completion normal-buy pricing."""
from pathlib import Path
import sys,inspect,json,gzip,hashlib,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
source=inspect.getsource(h.run);needle="    if 'real_base' in c:struct.pack_into('<Q',data,24,c['real_base'])";assert source.count(needle)==1
source=source.replace(needle,needle+"\n    if 'real_quote' in c:struct.pack_into('<Q',data,32,c['real_quote'])")
ns=dict(h.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);run=ns['run']
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for token in [False,True]:
 for fees in [[0,0,0],[95,30,5000],[333,777,2500]]:
  for pool_base,post in [(4,2),(6,3)]:
   c={'name':f'token-{token}-fees-{fees}-pool-{pool_base}-{post}','operation':'buy_v3','reserve_in':h.base_in,'reserve_out':h.base_out,'user_lamports':10**16,'real_base':1000000,'real_quote':10**9,'base_vault_amount':1000000+pool_base,'replace':13,'token_quote':token,'fees':fees,'amount':1000000+post,'max_cost':10**15,'trailing':[0]}
   if token:c['quote_fees']=fees
   o=run(R/'evidence/original/pump/deployed.so',c);n=run(a.candidate,c);assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'transformed_fixture_sha256':hashlib.sha256(source.encode()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print('total',len(rows),'mismatches',len(r['mismatches']))
