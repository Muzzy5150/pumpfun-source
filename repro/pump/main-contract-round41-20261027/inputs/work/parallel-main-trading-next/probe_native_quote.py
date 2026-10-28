from pathlib import Path
import argparse,json,gzip,hashlib
import quote_fixture as h
W=Path(__file__).resolve().parent;R=W.parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for op in ['buy_v3','sell_v3','buy_exact_quote_in_v3']:
  c={'operation':op,'amount':10**9,'max_cost':10**12 if op=='buy_v3' else 0 if op=='sell_v3' else 1,'reserve_in':h.base_in,'reserve_out':h.base_out,'native_quote_key_zero':True};o=h.run(R/'evidence/original/pump/deployed.so',c);b=h.run(a.candidate,c);diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data'] if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff});print(op,diff)
 a.output.write_bytes(gzip.compress(json.dumps({'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]},separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
