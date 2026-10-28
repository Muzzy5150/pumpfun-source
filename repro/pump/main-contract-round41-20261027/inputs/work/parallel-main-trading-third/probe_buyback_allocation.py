from pathlib import Path
import argparse,json,gzip,hashlib
import route_fixture as h
from event_parser import decode
W=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for rate in [1,100,10000]:
  for amount in [1015,1016,1020,1100,1500,1000000]:
   for maximum in [1,777,2**64-1]:
    c={'name':f'rate{rate}_amount{amount}_max{maximum}','single_hop':True,'extensions':{'A':{'transfer_fee':{'bps':rate,'maximum':maximum}}},'compute_unit_limit':600000,'account_mutations':{'curve_1':{'u64':[[24,1000]]},'global':{'u64':[[146,0]]}}}
    o=h.invoke(False,amount,'captured',case=c);b=h.invoke(False,amount,'captured',candidate=a.candidate,case=c);diff=[k for k in ['error','events','inner','return_data','before','after','pump_calls','token_calls'] if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff,'events_decoded':{'original':[decode(x) for x in o['events']],'candidate':[decode(x) for x in b['events']]}});print(c['name'],o['error'],diff,flush=True)
 a.output.write_bytes(gzip.compress(json.dumps({'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]},separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
