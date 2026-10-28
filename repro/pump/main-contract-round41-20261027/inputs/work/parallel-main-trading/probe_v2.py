from pathlib import Path
import sys,json,gzip,hashlib,argparse
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import buy_v2_fixture as h
parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,default=ROOT/'work/pump-legacy-cashback-order/fresh-main/candidate.so');parser.add_argument('--output',type=Path,default=ROOT/'work/parallel-main-trading/v2-probe-refreshed.json.gz');args=parser.parse_args();candidate=args.candidate
rows=[]
for kind in ['buy_v2','buy_exact_quote_in_v2']:
 for bps in [0,1,100,250,10000]:
  for cap in [0,1,2**64-1]:
   for amount in [1000000000]:
    c={'name':f'{kind}_fee_{bps}_{cap}_{amount}','kind':kind,'token_quote':True,'token22':True,'transfer_fee_bps':bps,'max_fee':cap,'amount':amount}
    a=h.run(c);b=h.run(c,candidate);diff=[k for k in ['error','accounts','events','inner','return_data'] if a[k]!=b[k]]
    rows.append({'case':c,'original':a,'candidate':b,'different_fields':diff,'match':not diff})
    print(c['name'],a['error'],b['error'],diff,flush=True)
for kind in ['buy_v2','buy_exact_quote_in_v2']:
 for role in ['associated_quote_bonding_curve','associated_quote_user','associated_quote_fee_recipient','associated_quote_buyback_fee_recipient','associated_creator_vault','associated_user_volume_accumulator']:
  for field,value in [(32,99),(108,0),(108,2)]:
   c={'name':f'{kind}_{role}_{field}_{value}','kind':kind,'token_quote':True,'account_mutations':{role:{'bytes':[[field,value]]}}}
   a=h.run(c);b=h.run(c,candidate);diff=[k for k in ['error','accounts','events','inner','return_data'] if a[k]!=b[k]]
   rows.append({'case':c,'original':a,'candidate':b,'different_fields':diff,'match':not diff})
   print(c['name'],a['error'],b['error'],diff,flush=True)
report={'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(h.__file__).read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if not r['match']]}
args.output.write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
