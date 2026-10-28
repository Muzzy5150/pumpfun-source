"""Signed native V3 buyback-key and validation-order counterexamples."""
from pathlib import Path
import argparse,gzip,hashlib,json,struct,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as v
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-match',action='store_true');a=p.parse_args()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();original=R/'evidence/original/pump/deployed.so';before={str(Path(p).resolve()):sha(p)for p in [__file__,v.__file__,v.f.__file__,a.candidate,original]};saved=dict(v.initial);ixs=list(v.f.ixs);rows=[]
for op in ['buy_v3','sell_v3','buy_exact_quote_in_v3']:
 for name in ['control','zero_unlisted','zero_listed','wrong_key','wrong_key_zero_amount','wrong_key_complete']:
  v.initial=dict(saved);v.f.ixs=list(ixs);ix=v.f.ixs[-1];metas=list(ix.accounts)
  if name!='control':
   zero=name.startswith('zero');key=v.f.Pubkey.default()if zero else v.f.Pubkey(bytes([92])*32)
   if not zero:v.initial[key]=v.f.Account(10**9,b'',v.f.Pubkey.default())
   metas[13]=v.f.AccountMeta(key,False,True)
   g=v.initial[v.global_key];data=bytearray(g.data);data[741:997]=(bytes(32)if name=='zero_listed'else bytes([91])*32)*8;v.initial[v.global_key]=v.f.Account(g.lamports,bytes(data),g.owner)
  if name=='wrong_key_complete':
   c=v.initial[v.curve];data=bytearray(c.data);data[48]=1;v.initial[v.curve]=v.f.Account(c.lamports,bytes(data),c.owner)
  v.f.ixs[-1]=v.f.Instruction(ix.program_id,ix.data,metas)
  c={'operation':op,'reserve_in':v.base_in,'reserve_out':v.base_out,'amount':0 if name=='wrong_key_zero_amount'else 10**9 if op!='sell_v3'else 500000000,'max_cost':10**12 if op=='buy_v3'else 0 if op=='sell_v3'else 1,'user_lamports':10**16}
  x=v.run(original,c);y=v.run(a.candidate,c);diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if x[k]!=y[k]];rows.append({'case':{'operation':op,'mutation':name},'original':x,'candidate':y,'different_fields':diff});print(op,name,x['error'],y['error'],diff,flush=True)
r={'scope':__doc__,'input_sha256':before,'candidate_sha256':sha(a.candidate),'original_sha256':sha(original),'case_count':len(rows),'cases':rows,'mismatches':[i for i,x in enumerate(rows)if x['different_fields']]};r['diagnostics']=audit({'buyback':r});a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));assert before=={k:sha(k)for k in before};print({'cases':len(rows),'mismatches':r['mismatches'],'diagnostic_mismatches':len(r['diagnostics']['mismatches'])})
if a.require_match:assert not r['mismatches']and not r['diagnostics']['mismatches']
