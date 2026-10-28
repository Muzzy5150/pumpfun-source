"""Signed default-key buyback rejection, with listed/nonlisted zero and valid controls."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,re,inspect
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_legacy_buy_differential as h
old=inspect.getsource(h.run)
new=old.replace("metas.append(f.AccountMeta(v3[13].pubkey,False,True))","metas.append(f.AccountMeta(f.Pubkey.default() if c.get('zero_buyback') else v3[13].pubkey,False,True))")
assert old!=new;exec(new,h.__dict__)
def diagnostics(r):return [re.sub(r' thrown in .*?:\d+\.', '.',v) for v in r['logs'] if 'AnchorError' in v or 'Left:' in v or 'Right:' in v]
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for kind in ['buy','buy_exact_sol_in']:
 for zero in [False,True]:
  for listed in [False,True]:
   c={'kind':kind,'amount':10**9,'minimum':10**12 if kind=='buy' else 1,'zero_buyback':zero,'name':f'{kind}-default-buyback-{zero}-zero-listed-{listed}'}
   if listed:c['account_mutations']={'global':{'bytes':[(i,0) for i in range(741,997)]}}
   o=h.run(c);n=h.run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64'];assert o['signatures_verified'] and n['signatures_verified'];diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];diff+=['diagnostics'] if diagnostics(o)!=diagnostics(n) else [];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'name':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'original_adapter_sha256':hashlib.sha256(old.encode()).hexdigest(),'modified_adapter_sha256':hashlib.sha256(new.encode()).hexdigest(),'cases':rows,'mismatches':[x['case']['name'] for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0))
