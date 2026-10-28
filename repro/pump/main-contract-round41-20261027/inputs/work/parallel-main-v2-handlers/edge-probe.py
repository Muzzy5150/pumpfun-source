import argparse, gzip, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import buy_fixture as b
from pump_diagnostic_audit import audit

p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
rows=[]
for kind in ['buy_v2','buy_exact_quote_in_v2']:
 for token in [False,True]:
  for partial in [False,True]:
   for scenario in ['ordinary','zero_input','zero_minimum','complete','empty_reserves','empty_reserves_complete']:
    for invalid_buyback in [False,True]:
     c={'name':f'{kind}_{token}_{partial}_{scenario}_{invalid_buyback}','kind':kind,'token_quote':token,'trailing':[int(partial)],'amount':500000000}
     if kind=='buy_exact_quote_in_v2':c['minimum']=1
     if scenario=='zero_input':c['amount']=0
     if scenario=='zero_minimum':c['minimum']=0
     if 'empty_reserves' in scenario:c.setdefault('account_mutations',{}).setdefault('bonding_curve',{})['u64']=[[24,0]]
     if 'complete' in scenario:c['curve_bytes']=[[48,1]]
     if invalid_buyback:c.setdefault('account_mutations',{})['global']={'bytes':[[i,0] for i in range(741,997)]}
     o=b.run(c);n=b.run(c,a.candidate);diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff})
     if diff:print(json.dumps({'case':c,'different_fields':diff,'original':o['error'],'candidate':n['error'],'original_anchor':[l for l in o['logs'] if 'AnchorError' in l],'candidate_anchor':[l for l in n['logs'] if 'AnchorError' in l]}),flush=True)
r={'cases':rows,'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'diagnostics':audit({'v2':rows})};a.output.write_bytes(gzip.compress(json.dumps(r).encode()));print(json.dumps({'cases':len(rows),'mismatches':len(r['mismatches']),'strict_mismatches':len(r['diagnostics']['mismatches'])}),flush=True)
