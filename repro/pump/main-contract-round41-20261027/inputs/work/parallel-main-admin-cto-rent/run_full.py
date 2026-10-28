"""Compressed signed admin CTO regression preserving exact errors, states, CPI and diagnostics."""
from pathlib import Path
import sys,argparse,json,gzip,hashlib,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_admin_cto_differential as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
def diag(r):return[re.sub(r' thrown in .*?:\d+\.', '.',s)for s in r['logs']if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
files=[Path(h.__file__),R/'evidence/original/pump/deployed.so',R/'evidence/original/pump_fees/deployed.so',R/'evidence/original/pump_amm/deployed.so',*[(R/f'evidence/dependencies/{n}/deployed.so')for n in ['spl_token','spl_token_2022','associated_token']],*[(R/'scripts'/n)for n in ['fees_donation_create_differential.py','fees_admin_differential.py','pump_validate_admin.py','pump_amm_admin_differential.py']],*[(R/f'evidence/upstream/{n}.json')for n in ['pump','pump_fees','pump_amm']],a.candidate,Path(__file__)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(p):sha(p)for p in files}
for i,c in enumerate(h.cases()):
 o=h.run(c);n=h.run(c,a.candidate);assert o['signatures_verified']and n['signatures_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','before','after','events','inner','return']if o[k]!=n[k]];diff+=['diagnostics']if diag(o)!=diag(n)else[];rows.append({'index':i,'case':c,'original':o,'candidate':n,'different_fields':diff})
 if diff:print(json.dumps({'index':i,'case':c['name'],'diff':diff,'original_error':o['error'],'candidate_error':n['error']}),flush=True)
assert all(sha(Path(p))==v for p,v in before.items());r={'scope':__doc__,'candidate_sha256':sha(a.candidate),'provenance':before,'case_count':len(rows),'cases':rows,'mismatches':[x['index']for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}));assert not r['mismatches']
