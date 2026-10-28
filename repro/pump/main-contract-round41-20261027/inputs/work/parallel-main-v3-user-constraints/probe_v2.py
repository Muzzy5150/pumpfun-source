"""Signed V3 user-token account constraints against the captured main program."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as v
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-match',action='store_true');a=p.parse_args()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();original=R/'evidence/original/pump/deployed.so'
inputs={str(Path(p).resolve()):sha(p)for p in [__file__,v.__file__,v.f.__file__,a.candidate,original]};saved_initial=dict(v.initial);saved_ixs=list(v.f.ixs);rows=[]
for op in ['buy_v3','sell_v3','buy_exact_quote_in_v3']:
 for mutation in ['user_mint','user_control','curve_authority','curve_token_program','curve_mint','curve_control']:
  v.initial=dict(saved_initial);v.f.ixs=list(saved_ixs);ix=v.f.ixs[-1];key=ix.accounts[6 if mutation.startswith('curve') else 9].pubkey;account=v.initial[key];data=bytearray(account.data);owner=account.owner
  if mutation=='curve_authority':data[32:64]=bytes([79])*32
  if mutation=='curve_token_program':
   legacy=v.f.Pubkey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');token22=v.f.Pubkey.from_string('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb');owner=legacy if owner==token22 else token22
  if mutation in ['user_mint','curve_mint']:data[:32]=bytes([78])*32
  v.initial[key]=v.f.Account(account.lamports,bytes(data),owner)
  case={'operation':op,'reserve_in':v.base_in,'reserve_out':v.base_out,'amount':10**9 if op!='sell_v3'else 500000000,'max_cost':10**12 if op=='buy_v3'else 0 if op=='sell_v3'else 1,'user_lamports':10**16}
  x=v.run(original,case);y=v.run(a.candidate,case);fields=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if x[k]!=y[k]];rows.append({'case':{'operation':op,'mutation':mutation},'original':x,'candidate':y,'different_fields':fields});print(op,mutation,x['error'],y['error'],fields,flush=True)
result={'scope':__doc__,'input_sha256':inputs,'candidate_sha256':sha(a.candidate),'original_sha256':sha(original),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};result['diagnostics']=audit({'user_constraints':result});a.output.write_bytes(gzip.compress(json.dumps(result).encode(),mtime=0));assert inputs=={k:sha(k)for k in inputs}
print({'cases':len(rows),'mismatches':result['mismatches'],'diagnostic_mismatches':len(result['diagnostics']['mismatches'])})
if a.require_match:assert not result['mismatches'] and not result['diagnostics']['mismatches']
