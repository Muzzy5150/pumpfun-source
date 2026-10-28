from pathlib import Path
import argparse,sys,json,gzip,hashlib,struct
W=Path(__file__).resolve().parent;R=W.parents[1];sys.path.insert(0,str(R/'scripts'))
import pump_buy_v2_differential as bv
import pump_sell_v2_differential as sv
import pump_legacy_buy_differential as lb
import pump_legacy_sell_differential as ls
import quote_extra_fixture as q

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for op in ['buy_v3','sell_v3','buy_exact_quote_in_v3']:
  for token in [False,True]:
   for enabled in [0,1]:
    for bps in [0,500,10000,2**64-1]:
     c={'name':f'{op}_{token}_{enabled}_{bps}','operation':op,'amount':10**9 if op!='sell_v3' else 500000000,'max_cost':2**64-1 if op=='buy_v3' else 0 if op=='sell_v3' else 1,'reserve_in':q.base_in,'reserve_out':q.base_out,'creator_override':bps,'global_bytes':[[1045,enabled]]}
     if token:c.update(token_quote=True,replace=13)
     o=q.run(R/'evidence/original/pump/deployed.so',c);b=q.run(a.candidate,c);diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data'] if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff});print(c['name'],diff,flush=True)
 for family,mod,kind in [('buy_v2',bv,'buy_v2'),('exact_v2',bv,'buy_exact_quote_in_v2'),('sell_v2',sv,None),('buy',lb,'buy'),('exact',lb,'buy_exact_sol_in'),('sell',ls,None)]:
  for token in ([False,True] if family.endswith('v2') else [False]):
   for enabled in [0,1]:
    for bps in [0,500,10000,2**64-1]:
     c={'name':f'{family}_{token}_{enabled}_{bps}','amount':10**9,'minimum':1 if family in ['exact','exact_v2'] else 2**64-1 if family in ['buy','buy_v2'] else 0,'curve_bytes':[(115+i,x) for i,x in enumerate(struct.pack('<Q',bps))],'account_mutations':{'global':{'bytes':[[1045,enabled]]}}}
     if kind:c['kind']=kind
     if family in ['buy','exact']:c['curve_u64']=[[115,bps]]
     if token:c['token_quote']=True
     o=mod.run(c);b=mod.run(c,a.candidate);diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff});print(c['name'],diff,flush=True)
 d={'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
