from pathlib import Path
import argparse,json,gzip,hashlib
import quote_extra_fixture as h
W=Path(__file__).resolve().parent;R=W.parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for filename in ['v3-post-reserve-original.json.gz','v3-post-counters-original.json.gz']:
  old=json.loads(gzip.decompress((W/filename).read_bytes()))
  for r in old:
   c=r['case'];o=h.run(R/'evidence/original/pump/deployed.so',c);b=h.run(a.candidate,c);fields=['error','accounts','inner_instructions','event_payloads','return_data'];assert all(o[k]==r['original'][k] for k in fields);diff=[k for k in fields if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff});print(filename,r.get('label'),o['error'],diff)
 a.output.write_bytes(gzip.compress(json.dumps({'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]},separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
