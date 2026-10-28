from pathlib import Path
import json,gzip,argparse,hashlib,route_fixture as h
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser();ap.add_argument('--candidate',type=Path,default=R/'work/pump-legacy-cashback-order/fresh-main/candidate.so');ap.add_argument('--output',type=Path,default=R/'work/parallel-main-trading/route-holder-refreshed.json.gz');args=ap.parse_args();b=args.candidate;rows=[]
for sell in [False,True]:
 for holder in [[],[0],[1],[0,1]]:
  for mode in ['captured','exotic','flat-fallback','legacy-flat']:
   for amount in [10**6,10**9]:
    case={'sell':sell,'holder':holder,'mode':mode,'amount':amount};o=h.invoke(sell,amount,mode,case=case);c=h.invoke(sell,amount,mode,candidate=b,case=case)
    fields=['error','events','inner','return_data','before','after','pump_calls','token_calls'];diff=[k for k in fields if o[k]!=c[k]]
    rows.append({'case':case,'original':o,'candidate':c,'different_fields':diff});print(case,o['error'],c['error'],diff,flush=True)
args.output.write_bytes(gzip.compress(json.dumps({'cases':rows,'case_count':len(rows),'candidate_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(h.__file__).read_bytes()).hexdigest(),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]},separators=(',',':')).encode(),mtime=0))
