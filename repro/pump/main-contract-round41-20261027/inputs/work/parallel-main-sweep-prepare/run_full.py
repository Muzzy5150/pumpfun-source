"""Full signed Sweep fixture, losslessly stored as gzip."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_fee_sweep_differential as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[Path(__file__),Path(h.__file__),a.candidate,R/'evidence/original/pump/deployed.so',R/'evidence/upstream/pump.json',Path(h.f.__file__),R/'evidence/original/pump_fees/deployed.so',R/'evidence/original/pump_amm/deployed.so']+[R/f'evidence/dependencies/{n}/deployed.so' for n in ['spl_token','spl_token_2022','associated_token']]
provenance={str(p):sha(p) for p in paths};rows=[]
for i,c in enumerate(h.cases()):
 o=h.run(c);n=h.run(c,a.candidate)
 assert o['signature_verification'] and n['signature_verification'] and o['transaction_base64']==n['transaction_base64']
 diff=[k for k in ['error','before','after'] if o[k]!=n[k]]
 diff += [k for k in ['return_data','inner_instructions'] if o['metadata'][k]!=n['metadata'][k]]
 if [l for l in o['logs'] if l.startswith('Program data: ')] != [l for l in n['logs'] if l.startswith('Program data: ')]:diff.append('events')
 rows.append(dict(case=c,original=o,candidate=n,different_fields=diff))
 if diff or (i+1)%25==0:print(json.dumps({'completed':i+1,'diff':diff}),flush=True)
assert provenance=={str(p):sha(p) for p in paths}
r={'scope':__doc__,'provenance':provenance,'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'cases':rows}
a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}))
if r['mismatches']:raise SystemExit(1)
