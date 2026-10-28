import sys,argparse,json,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import legacy_token22_fixture as f
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
all_keys=['associated_bonding_curve','pool_authority_mint_account','pool_base_token_account']
base={'boost':True,'token22_mint':True,'token22_atas':all_keys}
cases=[dict(base,token22_atas=all_keys[:i]) for i in [1,2,3]]
cases += [dict(base,readonly=name) for name in ['bonding_curve','associated_bonding_curve','pool_authority_mint_account','pool_base_token_account','pool_quote_token_account','user_pool_token_account']]
cases += [dict(base,wrong=name) for name in ['token_program','token_2022_program','associated_token_program','program']]
cases += [dict(base,unsigned=True),dict(base,complete=0),dict(base,mayhem=1),dict(base,repeat=True)]
cases += [dict(base,mutations={'associated_bonding_curve':{'patches':[(64,n.to_bytes(8,'little').hex())]}}) for n in [0,1,1000,1000000]]
cases += [dict(base,mutations={'mint':{'patches':[(44,bytes([n]).hex())]}}) for n in [0,6,9,18]]
cases += [dict(base,mutations={'associated_bonding_curve':{'patches':[(108,bytes([n]).hex())]}}) for n in [0,2]]
paths=[Path(__file__),Path(f.__file__),a.candidate,ROOT/'evidence/original/pump/deployed.so',ROOT/'evidence/original/pump_amm/deployed.so'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();provenance={str(p):sha(p) for p in paths}
for c in cases:
 o=f.run(c);n=f.run(c,a.candidate)
 for x in [o,n]:x['events']=[s for s in x['logs'] if s.startswith('Program data:')]
 diff=[k for k in ['error','before','after','events','inner','return'] if o[k]!=n[k]];row={'case':c,'original':o,'candidate':n,'different_fields':diff};rows.append(row)
 print(json.dumps({'case':c,'original_error':o['error'],'candidate_error':n['error'],'different_fields':diff,'original_anchor':[l for l in o['logs'] if 'AnchorError' in l],'candidate_anchor':[l for l in n['logs'] if 'AnchorError' in l]}),flush=True)
assert provenance=={str(p):sha(p) for p in paths}
r={'provenance':provenance,'cases':rows,'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'diagnostics':audit({'token22':rows})};a.output.write_bytes(gzip.compress(json.dumps(r).encode()))

print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches'],'diagnostic_mismatches':len(r['diagnostics']['mismatches'])}),flush=True)
assert not r['mismatches'] and not r['diagnostics']['mismatches']
