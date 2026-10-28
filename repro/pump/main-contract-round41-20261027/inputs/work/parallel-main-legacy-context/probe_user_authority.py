"""Signed legacy buy/sell associated-user authority probes, with valid controls."""
from pathlib import Path
import sys,json,gzip,hashlib,re,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_legacy_buy_differential as buy
import pump_legacy_sell_differential as sell
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for name,h in [('buy',buy),('sell',sell)]:
 for bad in [False,True]:
  c={'name':name+('-wrong-authority' if bad else '-control')}
  if bad:c['account_mutations']={'associated_user':{'bytes':[(i,77) for i in range(32,64)]}}
  o=h.run(c);n=h.run(c,a.candidate)
  diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]]
  rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff})
  print(json.dumps({'name':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff,'original_anchor':[x for x in o['logs'] if 'AnchorError' in x],'original_entered':any('Instruction: '+name.capitalize() in l for l in o['logs'])}),flush=True)
r={'scope':__doc__,'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'mismatches':[r['case']['name'] for r in rows if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0))
