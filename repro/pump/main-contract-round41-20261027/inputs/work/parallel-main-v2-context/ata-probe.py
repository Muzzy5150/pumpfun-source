import sys,json,gzip,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import buy_fixture as buy,sell_fixture as sell
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for kind,module in [('buy_v2',buy),('buy_exact_quote_in_v2',buy),('sell_v2',sell)]:
 for token_quote in [False,True]:
  for name,index in [('associated_base_bonding_curve',6),('associated_base_user',9)]:
   key=module.f.ixs[-1].accounts[index].pubkey;owner=module.INITIAL[key].owner;opposite=module.TOKEN if owner==module.TOKEN22 else module.TOKEN22
   for mode,mutation in [('owner',{'owner':str(opposite)}),('mint',{'bytes':[[0,module.INITIAL[key].data[0]^255]]}),('authority',{'bytes':[[32,module.INITIAL[key].data[32]^255]]})]:
    c={'kind':kind,'token_quote':token_quote,'amount':1,'account_mutations':{name:mutation}}
    o=module.run(c);n=module.run(c,a.candidate);diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];row={'case':{**c,'probe_mode':mode},'original':o,'candidate':n,'different_fields':diff};rows.append(row)
    print(json.dumps({'case':row['case'],'different_fields':diff,'original_error':o['error'],'candidate_error':n['error'],'original_anchor':[l for l in o['logs'] if 'AnchorError' in l],'candidate_anchor':[l for l in n['logs'] if 'AnchorError' in l]}),flush=True)
r={'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'diagnostics':audit({'v2':rows})};a.output.write_bytes(gzip.compress(json.dumps(r).encode()))
