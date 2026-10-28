"""Signed zero-real-token-reserve boundary with partial-fill controls."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_legacy_buy_differential as h
def diagnostics(r):return [re.sub(r' thrown in .*?:\d+\.', '.',v) for v in r['logs'] if 'AnchorError' in v or 'Left:' in v or 'Right:' in v]
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for kind in ['buy','buy_exact_sol_in']:
 for reserve in [0,1]:
  for partial in [0,1]:
   c={'kind':kind,'amount':1 if kind=='buy' else 10**9,'minimum':10**12 if kind=='buy' else 1,'curve_u64':[[24,reserve]],'trailing':[0,partial],'name':f'{kind}-reserve-{reserve}-partial-{partial}'}
   o=h.run(c);n=h.run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64'];assert o['signatures_verified'] and n['signatures_verified'];diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];diff+=['diagnostics'] if diagnostics(o)!=diagnostics(n) else [];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'name':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'mismatches':[x['case']['name'] for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0))
