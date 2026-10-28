from pathlib import Path
import argparse,json,gzip,hashlib
import route_fixture as h
from event_parser import decode
W=Path(__file__).resolve().parent

def cases():
 for sell in [False,True]:
  for single in [False,True]:
   for labels in [['A'],['B'],['A','B']]:
    for name,spec in [('zero',{'bps':0}),('one',{'bps':1}),('one_cap1',{'bps':1,'maximum':1}),('pct1',{'bps':100}),('pct1_cap7',{'bps':100,'maximum':7}),('pct100',{'bps':10000}),('pct100_cap7',{'bps':10000,'maximum':7})]:
     for amount in [1,7,1000,1000000]:
      yield {'name':f'{sell}_{single}_{"".join(labels)}_{name}_{amount}','sell':sell,'single_hop':single,'amount':amount,'compute_unit_limit':600000,'extensions':{label:{'transfer_fee':spec} for label in labels}}
 for sell in [False,True]:
  for single in [False,True]:
   for epoch in [0,99,100,101]:
    yield {'name':f'epoch_{sell}_{single}_{epoch}','sell':sell,'single_hop':single,'amount':1000000,'compute_unit_limit':600000,'epoch':epoch,'extensions':{'A':{'transfer_fee':{'bps':100,'maximum':777,'new_epoch':100,'new_bps':700,'new_maximum':555}}}}
 # Parsed but inactive extensions, token program enforcement, and preexisting withheld state.
 ext_specs=[('close_authority',{'mint_tlvs':[[3,'00'*32]]}),('default_initialized',{'mint_tlvs':[[6,'01']]}),('permanent_delegate',{'mint_tlvs':[[12,'00'*32]]}),('metadata_pointer',{'mint_tlvs':[[18,'00'*64]]}),('disabled_hook',{'mint_tlvs':[[14,'00'*64]],'account_tlvs':[[15,'00']]}),('memo_off',{'account_tlvs':[[8,'00']]}),('memo_on',{'account_tlvs':[[8,'01']]}),('guard_off',{'account_tlvs':[[11,'00']]}),('guard_on',{'account_tlvs':[[11,'01']]}),('fee_withheld',{'transfer_fee':{'bps':100},'withheld':777,'immutable_owner':True})]
 for sell in [False,True]:
  for single in [False,True]:
   for name,spec in ext_specs:
    yield {'name':f'extension_{sell}_{single}_{name}','sell':sell,'single_hop':single,'amount':1000000,'compute_unit_limit':600000,'extensions':{'A':spec,'B':spec}}
 # Completion with active quote transfer fee and independent final base fee.
 for single in [False,True]:
  for labels in [['A'],['B'],['A','B']]:
   for rate in [0,1,100,10000]:
    yield {'name':f'completion_{single}_{"".join(labels)}_{rate}','sell':False,'single_hop':single,'amount':1000000,'compute_unit_limit':600000,'extensions':{label:{'transfer_fee':{'bps':rate,'maximum':777}} for label in labels},'account_mutations':{'curve_1':{'u64':[[24,1000]]},'global':{'u64':[[146,0]]}}}

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for c in cases():
  o=h.invoke(c['sell'],c['amount'],'captured',candidate=None,case=c);b=h.invoke(c['sell'],c['amount'],'captured',candidate=a.candidate,case=c);diff=[k for k in ['error','events','inner','return_data','before','after','pump_calls','token_calls'] if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff,'events_decoded':{'original':[decode(x) for x in o['events']],'candidate':[decode(x) for x in b['events']]}});print(c['name'],o['error'],diff,flush=True)
 d={'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(h.__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
