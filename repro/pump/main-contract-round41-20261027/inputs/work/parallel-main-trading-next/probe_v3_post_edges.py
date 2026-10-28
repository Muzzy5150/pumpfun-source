from pathlib import Path
import argparse,json,gzip,hashlib
import quote_extra_fixture as h
from event_parser import decode
W=Path(__file__).resolve().parent;R=W.parents[1]
def cases():
 for real in [0,1,2]:
  for amount in [4,5,6,7,8,9,10,11,1000]:
   yield {'name':f'cap{real}_amount{amount}','operation':'buy_exact_quote_in_v3','amount':amount,'max_cost':1,'reserve_in':1000,'reserve_out':1000,'real_base':real,'base_vault_amount':1000,'user_lamports':10**16,'curve_qwords':[[32,1000],[150,10000],[158,10000]],'global_bytes':[(146+i,0) for i in range(8)]}
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for c in cases():
  o=h.run(R/'evidence/original/pump/deployed.so',c);r={'case':c,'original':o,'events_decoded':[decode(x) for x in o['event_payloads']]}
  if a.candidate:
   b=h.run(a.candidate,c);r.update(candidate=b,different_fields=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data'] if o[k]!=b[k]])
  rows.append(r);print(c['name'],o['error'],[(x['event'],x.get('quote_amount'),x.get('base_out'),x.get('quote_in')) for x in r['events_decoded']],r.get('different_fields'),flush=True)
 a.output.write_bytes(gzip.compress(json.dumps({'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest() if a.candidate else None,'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r.get('different_fields')]},separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
