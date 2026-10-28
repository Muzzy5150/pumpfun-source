from pathlib import Path
import argparse,json,gzip,hashlib
import route_fixture as h
from event_parser import decode
W=Path(__file__).resolve().parent;R=W.parents[1]
def cases():
 for sell in [False,True]:
  for labels in [['A'],['B'],['A','B']]:
   for mode,spec in [('plain',{}),('immutable',{'immutable_owner':True}),('fee1',{'transfer_fee':{'bps':100}}),('fee1cap7',{'transfer_fee':{'bps':100,'maximum':7}}),('fee100',{'transfer_fee':{'bps':10000}}),('frozen',{'frozen':True})]:
    yield {'name':f'{"sell" if sell else "buy"}_{"".join(labels)}_{mode}','sell':sell,'amount':10**6,'compute_unit_limit':600000,'extensions':{label:spec for label in labels}}
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for c in cases():
  o=h.invoke(c['sell'],c['amount'],'captured',candidate=None,case=c);b=h.invoke(c['sell'],c['amount'],'captured',candidate=a.candidate,case=c);diff=[k for k in ['error','events','inner','return_data','before','after','pump_calls','token_calls'] if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff,'events_decoded':{'original':[decode(x) for x in o['events']],'candidate':[decode(x) for x in b['events']]}});print(c['name'],o['error'],diff,flush=True)
 d={'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(h.__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
