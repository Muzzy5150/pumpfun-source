from pathlib import Path
import json,gzip,argparse,hashlib
import completion_fixture as h
W=Path(__file__).resolve().parent
FIELDS=['error','events','inner','return_data','before','after','pump_calls','token_calls']
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for filename in ['completion-original.json.gz','post-budget-original.json.gz','post-ratio-original.json.gz']:
  d=json.loads(gzip.decompress((W/filename).read_bytes()));data=d['cases'] if isinstance(d,dict) else d
  for r in data:
   c=r['case'];amount=c.get('amount',r.get('amount'));o=h.invoke(False,amount,'captured',case=c);b=h.invoke(False,amount,'captured',candidate=a.candidate,case=c);diff=[k for k in FIELDS if o[k]!=b[k]];prior=[k for k in FIELDS if o[k]!=r['original'][k]];assert not prior,(filename,c,prior)
   rows.append({'dataset':filename,'case':c,'amount':amount,'original':o,'candidate':b,'different_fields':diff,'match':not diff});print(filename,c['name'],o['error'],b['error'],diff,flush=True)
 d={'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows) if not r['match']],'cases':rows};a.output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
