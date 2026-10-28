"""Signed captured-loader probes for V3 context account ownership and rent constraints."""
from pathlib import Path
import argparse,sys,json,gzip,hashlib,copy
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import pump_v3_configured_fee_differential as v
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-match',action='store_true');a=p.parse_args()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs={str(Path(p).resolve()):sha(p) for p in [__file__,v.__file__,v.f.__file__,a.candidate,ROOT/'evidence/original/pump/deployed.so']}
original=ROOT/'evidence/original/pump/deployed.so';saved_initial=dict(v.initial);saved_ixs=list(v.f.ixs);rows=[]
for operation in ['buy_v3','sell_v3','buy_exact_quote_in_v3']:
 for mutation in ['none','uva_rent_low','uva_empty','uva_wrong_owner','uva_new','uva_bad_discriminator','uva_short','uva_stored_user','fee_stored_bump','program_wrong_key','program_not_executable','uva_readonly','uva_wrong_key']:
  v.initial=dict(saved_initial);v.f.ixs=list(saved_ixs);ix=v.f.ixs[-1];metas=list(ix.accounts)
  uva=metas[11].pubkey
  if mutation in ['uva_rent_low','uva_empty','uva_wrong_owner','uva_new','uva_bad_discriminator','uva_short','uva_stored_user']:
   acc=v.initial[uva];lamports=1 if mutation=='uva_rent_low' else acc.lamports;data=b'' if mutation=='uva_empty' else acc.data;owner=v.f.Pubkey.default() if mutation=='uva_wrong_owner' else acc.owner
   if mutation=='uva_new':lamports=0;data=b'';owner=v.f.Pubkey.default()
   if mutation=='uva_bad_discriminator':data=bytes([data[0]^1])+data[1:]
   if mutation=='uva_short':data=data[:81]
   if mutation=='uva_stored_user':data=data[:8]+bytes([79])*32+data[40:]
   v.initial[uva]=v.f.Account(lamports,data,owner)
  if mutation=='fee_stored_bump':
   acc=v.initial[v.fee_key];data=bytearray(acc.data);data[8]^=1;v.initial[v.fee_key]=v.f.Account(acc.lamports,bytes(data),acc.owner)
  if mutation=='program_wrong_key':metas[-1]=v.f.AccountMeta(v.f.Pubkey.default(),False,False)
  if mutation=='program_not_executable':
   # The replacement is present but not the current program; avoid mutating the executing program's loader state.
   other=v.f.Pubkey(bytes([91])*32);v.initial[other]=v.f.Account(10**9,b'',v.f.Pubkey.default(),False);metas[-1]=v.f.AccountMeta(other,False,False)
  if mutation=='uva_readonly':metas[11]=v.f.AccountMeta(uva,False,False)
  if mutation=='uva_wrong_key':
   other=v.f.Pubkey(bytes([92])*32);v.initial[other]=v.initial[uva];metas[11]=v.f.AccountMeta(other,False,True)
  v.f.ixs[-1]=v.f.Instruction(ix.program_id,ix.data,metas)
  c={'operation':operation,'reserve_in':v.base_in,'reserve_out':v.base_out,'amount':10**9 if operation!='sell_v3' else 500000000,'max_cost':10**12 if operation=='buy_v3' else 0 if operation=='sell_v3' else 1,'user_lamports':10**16}
  x=v.run(original,c);y=v.run(a.candidate,c);fields=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data'] if x[k]!=y[k]]
  rows.append({'case':{'operation':operation,'mutation':mutation},'original':x,'candidate':y,'different_fields':fields})
  print(operation,mutation,fields,flush=True)
result={'scope':__doc__,'input_sha256':inputs,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};result['diagnostics']=audit({'v3_context':result});a.output.write_bytes(gzip.compress(json.dumps(result,separators=(',',':')).encode(),mtime=0));print({'cases':len(rows),'mismatches':result['mismatches'],'diagnostic_mismatches':len(result['diagnostics']['mismatches'])})

assert inputs=={p:sha(p)for p in inputs}
if a.require_match:assert not result["mismatches"] and not result["diagnostics"]["mismatches"]
