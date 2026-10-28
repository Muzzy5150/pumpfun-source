"""Signed V3 buy zero-reserve and token-clipping probes using captured main loader."""
from pathlib import Path
import sys,argparse,json,gzip,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import pump_v3_configured_fee_differential as v
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-match',action='store_true');a=p.parse_args();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();original=ROOT/'evidence/original/pump/deployed.so';inputs={str(Path(p).resolve()):sha(p)for p in [__file__,v.__file__,v.f.__file__,a.candidate,original]};rows=[]
for token in [False,True]:
 for real_base,amount in [(0,0),(0,1),*[(1000000,n)for n in [0,999999,1000000,1000001,2000000]]]:
  for partial in [0,1]:
   c={'operation':'buy_v3','reserve_in':v.base_in,'reserve_out':v.base_out,'amount':amount,'max_cost':10**15,'user_lamports':10**16,'real_base':real_base,'token_quote':token,'replace':13,'trailing':[partial]}
   x=v.run(original,c);y=v.run(a.candidate,c);fields=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if x[k]!=y[k]];rows.append({'case':c,'original':x,'candidate':y,'different_fields':fields});print(token,amount,partial,fields,flush=True)
r={'scope':__doc__,'input_sha256':inputs,'case_count':len(rows),'mismatches':[i for i,x in enumerate(rows)if x['different_fields']],'cases':rows};r['diagnostics']=audit({'v3_partial':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));assert inputs=={p:sha(p)for p in inputs};print(len(rows),len(r['mismatches']),len(r['diagnostics']['mismatches']));
if a.require_match:assert not r['mismatches'] and not r['diagnostics']['mismatches']
