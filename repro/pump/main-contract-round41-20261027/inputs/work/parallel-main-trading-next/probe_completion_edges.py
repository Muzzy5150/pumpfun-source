from pathlib import Path
import argparse,json,gzip,hashlib
import completion_fixture as h
from event_parser import decode
W=Path(__file__).resolve().parent

def cases():
 for pos in [0,1]:
  for cap in [10**9,10**12,10**13]:
   yield {'name':f'large_{pos}_{cap}','amount':10**9,'account_mutations':{f'curve_{pos}':{'u64':[[24,cap]]},'global':{'u64':[[146,0],[997,3333]]}}}
  yield {'name':f'holder_{pos}','amount':10**9,'account_mutations':{f'curve_{pos}':{'u64':[[24,1000000]],'bytes':[[124,1]]},'global':{'u64':[[146,0]]}}}
  yield {'name':f'fee_counters_{pos}','amount':10**9,'account_mutations':{f'curve_{pos}':{'u64':[[24,1000000],[125,10000],[133,20000],[150,2**64-1],[158,2**64-1]]},'global':{'u64':[[146,0]]}}}
  for field in [125,133]:
   yield {'name':f'fee_overflow_{pos}_{field}','amount':10**9,'account_mutations':{f'curve_{pos}':{'u64':[[24,1000000],[field,2**64-1]]},'global':{'u64':[[146,0]]}}}
 yield {'name':'both_complete','amount':10**9,'account_mutations':{'curve_0':{'u64':[[24,1000000]]},'curve_1':{'u64':[[24,1000000]]},'global':{'u64':[[146,0]]}}}
 yield {'name':'both_complete_budgeted','amount':10**9,'compute_unit_limit':600000,'account_mutations':{'curve_0':{'u64':[[24,1000000]]},'curve_1':{'u64':[[24,1000000]]},'global':{'u64':[[146,0]]}}}
 yield {'name':'creator_zero','amount':10**9,'account_mutations':{'curve_1':{'u64':[[24,1000000]],'bytes':[[i,0] for i in range(49,81)]},'global':{'u64':[[146,0]]}}}
 for amount in [3,4,5,6,7]:
  for migration in [0,10**9]:
   yield {'name':f'native_small_{amount}_{migration}','amount':amount,'account_mutations':{'curve_0':{'u64':[[24,0]]},'global':{'u64':[[146,migration]]}}}

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--compute-unit-limit',type=int);a=p.parse_args();rows=[]
 for c in cases():
  if a.compute_unit_limit:c['compute_unit_limit']=a.compute_unit_limit
  o=h.invoke(False,c['amount'],'captured',case=c);r={'case':c,'original':o,'events_decoded':[decode(e) for e in o['events']]}
  if a.candidate:
   b=h.invoke(False,c['amount'],'captured',candidate=a.candidate,case=c);diff=[k for k in ['error','events','inner','return_data','before','after','pump_calls','token_calls'] if o[k]!=b[k]];r.update(candidate=b,different_fields=diff,match=not diff)
  rows.append(r);print(c['name'],o['error'],r.get('different_fields'),flush=True)
 d={'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest() if a.candidate else None,'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r.get('match') is False]};a.output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
