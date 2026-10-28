import sys,json,gzip,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import buy_fixture as buy,sell_fixture as sell
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for kind,module in [('buy_v2',buy),('buy_exact_quote_in_v2',buy),('sell_v2',sell)]:
 basekey=module.f.ixs[-1].accounts[1].pubkey;baseowner=module.INITIAL[basekey].owner;opposite=module.TOKEN if baseowner==module.TOKEN22 else module.TOKEN22
 for token_quote in [False,True]:
  for mode in ['base_owner','quote_owner','alternate_user','alternate_curve']:
   c={'kind':kind,'token_quote':token_quote,'amount':1}
   if mode=='base_owner':c['account_mutations']={'base_mint':{'owner':str(opposite)}}
   elif mode=='quote_owner':c['account_mutations']={'quote_mint':{'owner':str(module.TOKEN22)}}
   else:c['wrong_keys']=['associated_base_user' if mode=='alternate_user' else 'associated_base_bonding_curve']
   o=module.run(c);n=module.run(c,a.candidate);diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];row={'case':{**c,'mode':mode},'original':o,'candidate':n,'different_fields':diff};rows.append(row)
   print(json.dumps({'case':row['case'],'different_fields':diff,'original_error':o['error'],'candidate_error':n['error'],'original_anchor':[l for l in o['logs'] if 'AnchorError' in l],'candidate_anchor':[l for l in n['logs'] if 'AnchorError' in l]}),flush=True)
r={'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'diagnostics':audit({'v2':rows})};a.output.write_bytes(gzip.compress(json.dumps(r).encode()))
