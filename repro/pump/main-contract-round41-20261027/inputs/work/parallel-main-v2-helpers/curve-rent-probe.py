import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import buy_fixture as b
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for kind in ['buy_v2','buy_exact_quote_in_v2']:
 for balance in [100000,10000000]:
  for reserve in [10**10,10**12]:
   c={'name':f'{kind}_{balance}_{reserve}','kind':kind,'amount':1000,'minimum':1 if kind=='buy_exact_quote_in_v2' else 10**12,'account_mutations':{'bonding_curve':{'lamports':balance,'u64':[[32,reserve]]}}}
   o=b.run(c);n=b.run(c,a.candidate);diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],diff,o['error'],n['error'],flush=True)
d=audit({'curve_rent':rows});a.output.write_bytes(gzip.compress(json.dumps({'cases':rows,'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'diagnostics':d}).encode()))
