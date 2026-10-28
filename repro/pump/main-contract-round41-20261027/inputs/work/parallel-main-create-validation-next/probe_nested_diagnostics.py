#!/usr/bin/env python3
"""Signed nested creation vault state/length diagnostics with valid unchanged account owners."""
from pathlib import Path
import sys,importlib.util,copy,json,hashlib,gzip,argparse,re
ROOT=Path(__file__).resolve().parents[2];H=ROOT/'work/pump-nested-current21/proposed';sys.path.insert(0,str(H));sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('nested_general',H/'pump_nested_general_differential.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
inputs=[Path(__file__),H/'pump_nested_general_differential.py',H/'pump_create_nested_fixture.py',H/'proposal_common.py',a.candidate,ROOT/'evidence/original/pump/deployed.so'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(p):sha(p) for p in inputs}
case={'id':'pool-immediate-depth-1','depth':1,'pool_positions':[0],'pool_adjustment':0,'asymmetric':False,'expected':'success'};base,layout=f.fixture(case);rows=[]
def diag(r):return[re.sub(r' thrown in .*?:\d+\.', '.',s)for s in r['logs']if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
mutations=[('state-'+str(v),lambda b,v=v:b.__setitem__(108,v))for v in [0,1,2,3,255]]
for n in [164,165,166,354,355,356]:
 def resize(b,n=n):
  if n>len(b):b.extend(bytes(n-len(b)))
  else:del b[n:]
  if n>165:b[165]=2
 mutations.append(('length-'+str(n),resize))
for side,index in [('base',2),('quote',3)]:
 for label,mut in mutations:
  child=copy.deepcopy(base);key=layout['groups_nearest_first'][0][index];record=child['bootstrap_accounts'][key];blob=bytearray.fromhex(record['data']);mut(blob);record['data']=blob.hex()
  x=f.h.run(child);y=f.h.run(child,a.candidate)
  for r in [x,y]:
   assert r['verified_signature_count']==2
   assert not any(' invoke ['in l and(l.startswith('Program MAyhSmz')or l.startswith('Program pAMM'))for l in r['logs'])
  diff=[k for k in ['before','after','error','events','inner','return']if x[k]!=y[k]];diff+=['diagnostics']if diag(x)!=diag(y)else[];rows.append({'case':{'side':side,'mutation':label},'fixture':child,'original':x,'candidate':y,'different_fields':diff});print(side,label,x['error'],y['error'],diff,flush=True)
assert before=={str(p):sha(p)for p in inputs};report={'scope':__doc__,'inputs_sha256':before,'candidate_sha256':sha(a.candidate),'original_sha256':sha(ROOT/'evidence/original/pump/deployed.so'),'cases':rows,'case_count':len(rows),'mismatches':[r['case']for r in rows if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0));print('cases',len(rows),'mismatches',len(report['mismatches']),flush=True)
