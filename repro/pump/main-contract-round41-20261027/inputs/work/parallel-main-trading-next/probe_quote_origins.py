from pathlib import Path
import argparse,json,gzip,hashlib
import quote_fixture as h
W=Path(__file__).resolve().parent;R=W.parents[1]
def cases():
 for op in ['buy_v3','sell_v3','buy_exact_quote_in_v3']:
  base={'operation':op,'amount':10**9 if op!='sell_v3' else 500000000,'max_cost':10**12 if op=='buy_v3' else 0 if op=='sell_v3' else 1,'reserve_in':h.base_in,'reserve_out':h.base_out,'user_lamports':10**16}
  for token in [False,True]:
   for low in [False,True]:
    c={**base,'name':f'{op}_{token}_{low}'}
    if token:c.update(token_quote=True,replace=13,quote_mutation='curve_address')
    else:c['native_wrong_curve_address']=True
    if low:c['curve_lamports']=100000
    yield c

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for c in cases():
  o=h.run(R/'evidence/original/pump/deployed.so',c);r={'case':c,'original':o}
  if a.candidate:
   b=h.run(a.candidate,c);r.update(candidate=b,different_fields=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data'] if o[k]!=b[k]])
  rows.append(r);print(c['name'],o['error'],len(o['inner_instructions']),[x for x in o['logs'] if 'AnchorError' in x or 'invoke' in x],flush=True)
 a.output.write_bytes(gzip.compress(json.dumps({'case_count':len(rows),'cases':rows},separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
