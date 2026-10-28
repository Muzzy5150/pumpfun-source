from pathlib import Path
import argparse,gzip,json,sys,hashlib
from audit_results import messages
import quote_extension_fixture as q
import route_fixture as h
W=Path(__file__).resolve().parent;R=W.parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for layout in ['unknown_only','unknown_first','unknown_last','unknown_overrun','known_only','known_overrun','known_badlen','known_short_header','duplicate_bad','duplicate_valid','unknown_duplicate','close_duplicate','known_tail_one','known_tail_nonzero']:
  for op in ['buy_v3','sell_v3','buy_exact_quote_in_v3']:
   c={'name':op+'_'+layout,'operation':op,'amount':1000000,'max_cost':10**12 if op=='buy_v3' else 1 if op.startswith('buy_exact') else 0,'reserve_in':q.base_in,'reserve_out':q.base_out,'token_quote':True,'quote2022':True,'replace':13,'extension':True,'bps':100,'quote_mint_layout':layout}
   o=q.run(R/'evidence/original/pump/deployed.so',c);b=q.run(a.candidate,c);fields=['error','accounts','inner_instructions','event_payloads','return_data'];diff=[k for k in fields if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff});print(c['name'],o['error'],diff,flush=True)
 for sell in [False,True]:
  for placement in ['only','first','last','overrun']:
   ext={'mint_tlvs':[[65000,'00']]}
   # transfer-fee extension comes first in this route fixture, then extra TLVs.
   if placement=='last':ext['transfer_fee']={'bps':100}
   if placement=='first':ext={'transfer_fee':{'bps':100},'mint_tlvs_prefix':[[65000,'00']]}
   if placement=='overrun':ext['mint_tlvs']=[[65000,'00']];ext['mint_length']=170
   c={'name':f'route_{sell}_{placement}','sell':sell,'single_hop':True,'compute_unit_limit':600000,'extensions':{'A':ext}}
   o=h.invoke(sell,1000000,'captured',case=c);b=h.invoke(sell,1000000,'captured',candidate=a.candidate,case=c);fields=['error','events','inner','return_data','before','after','pump_calls','token_calls'];diff=[k for k in fields if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff});print(c['name'],o['error'],diff,flush=True)
 d={'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
