from pathlib import Path
import argparse,random,json,gzip,hashlib
import completion_fixture as h
from audit_results import messages
W=Path(__file__).resolve().parent

def cases():
 rng=random.Random(137)
 for i in range(120):
  pos=rng.randrange(2);amount=rng.choice([3,4,5,7,10,100,1000,1000000,10**9]);pb=rng.choice([0,1,95,3333,10000,20000]);cb=rng.choice([0,1,30,5000,10000,20000]);rq=rng.choice([1,100,10**6,10**9] if pos==0 else [10**6,10**12,10**15,10**18]);cap=rng.choice([0,1,2,10,100]);buyback=rng.choice([0,1,3333,5000,10000]);migration=rng.choice([0,1,rq,max(0,rq-1)])
  vm={'curve_0':{'u64':[[8,10**6],[16,10**6],[24,10**6]]},'curve_1':{'u64':[[8,1000],[16,1000],[24,1000]]},'global':{'u64':[[146,migration],[997,buyback]]}}
  vm[f'curve_{pos}']['u64'] += [[24,cap],[32,rq],[150,rng.choice([0,10000])],[158,rng.choice([0,10000])]]
  if rng.randrange(5)==0:vm[f'curve_{pos}']['bytes']=[[j,0] for j in range(49,81)]
  elif rng.randrange(5)==0:vm[f'curve_{pos}']['bytes']=[[124,1]]
  yield {'name':f'fuzz_{i}_pos{pos}_a{amount}_p{pb}_c{cb}','amount':amount,'fees':[pb,cb],'compute_unit_limit':600000,'account_mutations':vm}

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for c in cases():
  o=h.invoke(False,c['amount'],'captured',case=c);b=h.invoke(False,c['amount'],'captured',candidate=a.candidate,case=c);diff=[k for k in ['error','events','inner','return_data','before','after','pump_calls','token_calls'] if o[k]!=b[k]];di=messages(o['logs'])!=messages(b['logs']);rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff,'diagnostic_mismatch':di});print(c['name'],o['error'],b['error'],diff,di,flush=True)
 a.output.write_bytes(gzip.compress(json.dumps({'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields'] or r['diagnostic_mismatch']]},separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
