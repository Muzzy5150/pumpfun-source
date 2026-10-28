from pathlib import Path
import argparse,json,gzip,hashlib
import route_fixture as h
from event_parser import decode
W=Path(__file__).resolve().parent

def cases():
 for sell in [False,True]:
  for pf,cf in [(2**64-1,0),(0,2**64-1),(2**64-1,2**64-1),(2**64-96,95),(10000,10000),(0,0)]:
   for bps in [0,10000]:
    for amount in [1,1000000]:
     yield {'name':f'fees_{sell}_{pf}_{cf}_{bps}_{amount}','sell':sell,'single_hop':True,'amount':amount,'fees':[pf,cf],'extensions':{'A':{'transfer_fee':{'bps':bps}}},'compute_unit_limit':600000}
 for sell in [False,True]:
  for single in [False,True]:
   for name,ext in [('default_frozen',{'mint_tlvs':[[6,'02']]}),('nontransferable',{'mint_tlvs':[[9,'']],'account_tlvs':[[13,'']]}),('hook_disabled',{'mint_tlvs':[[14,'00'*64]],'account_tlvs':[[15,'00']]}),('invalid_tlv',{'mint_tlvs':[[65000,'00']]}),('short_fee',{'transfer_fee':{'bps':100},'mint_length':200})]:
    yield {'name':f'state_{sell}_{single}_{name}','sell':sell,'single_hop':single,'amount':1000000,'extensions':{'A':ext,'B':ext},'compute_unit_limit':600000}

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for c in cases():
  o=h.invoke(c['sell'],c['amount'],'captured',candidate=None,case=c);b=h.invoke(c['sell'],c['amount'],'captured',candidate=a.candidate,case=c);diff=[k for k in ['error','events','inner','return_data','before','after','pump_calls','token_calls'] if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff,'events_decoded':{'original':[decode(x) for x in o['events']],'candidate':[decode(x) for x in b['events']]}});print(c['name'],o['error'],diff,flush=True)
 a.output.write_bytes(gzip.compress(json.dumps({'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]},separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
