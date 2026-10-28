import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import buy_fixture as b
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
data=b.INITIAL[b.FEE].data;offsets=[57];position=65
for _ in range(2):
 count=struct.unpack_from('<I',data,position)[0];position+=4
 for i in range(count):offsets.append(position+32);position+=40
offsets.append(position+16)
for kind in ['buy_v2','buy_exact_quote_in_v2']:
 for token in [False,True]:
  for balance in [0,1]:
   c={'name':f'{kind}_{token}_{balance}_fee_zero','kind':kind,'token_quote':token,'amount':500000000,'minimum':1 if kind=='buy_exact_quote_in_v2' else 10**12,'account_mutations':{'creator_vault':{'lamports':balance},'fee_config':{'u64':[[i,0] for i in offsets]}}}
   o=b.run(c);n=b.run(c,a.candidate);diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],diff,o['error'],n['error'],flush=True)
d=audit({'zero_fee':rows});a.output.write_bytes(gzip.compress(json.dumps({'cases':rows,'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'diagnostics':d}).encode()))
