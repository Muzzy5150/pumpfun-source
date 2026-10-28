from pathlib import Path
import json,gzip,argparse
import quote_extra_fixture as h
from event_parser import decode
W=Path(__file__).resolve().parent;R=W.parents[1];p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for pb,cb in [(95,30),(0,20000),(20000,0),(5000,5000)]:
 for amount in [7,10,100,1000]:
  for cap in [0,1]:
   c={'name':f'p{pb}_c{cb}_a{amount}_cap{cap}','operation':'buy_exact_quote_in_v3','amount':amount,'max_cost':1,'reserve_in':1000,'reserve_out':1000,'real_base':cap,'base_vault_amount':1000,'user_lamports':10**16,'curve_qwords':[[32,1000],[150,0],[158,0]],'global_bytes':[(146+i,0) for i in range(8)],'fees':[pb,cb,5000]}
   o=h.run(R/'evidence/original/pump/deployed.so',c);b=h.run(a.candidate,c);diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data'] if o[k]!=b[k]];ev=[decode(x) for x in o['event_payloads']];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff,'events_decoded':ev});print(c['name'],o['error'],b['error'],diff,[(x['event'],x.get('quote_amount'),x.get('base_out'),x.get('quote_in')) for x in ev],flush=True)
a.output.write_bytes(gzip.compress(json.dumps({'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]},separators=(',',':')).encode(),mtime=0))
