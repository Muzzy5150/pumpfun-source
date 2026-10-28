#!/usr/bin/env python3
"""Signed nested-create pool vault-link mismatches; supplied keys/owners and PDA derivation stay fixed."""
from pathlib import Path
import sys,importlib.util,copy,json,hashlib,gzip,argparse,re
ROOT=Path(__file__).resolve().parents[2];H=ROOT/'work/pump-nested-current21/proposed';sys.path.insert(0,str(H));sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('nested_general',H/'pump_nested_general_differential.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
inputs=[Path(__file__),H/'pump_nested_general_differential.py',H/'pump_create_nested_fixture.py',H/'proposal_common.py',a.candidate,ROOT/'evidence/original/pump/deployed.so'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(p):sha(p)for p in inputs}
base,layout=f.fixture({'id':'pool-immediate-depth-1','depth':1,'pool_positions':[0],'pool_adjustment':0,'asymmetric':False,'expected':'success'});poolkey=layout['groups_nearest_first'][0][1]
cases=[('valid',[])]
for side,off in [('base',139),('quote',171)]:
 for label,key in [('zero',bytes(32)),('ones',bytes([1])*32),('user',bytes(f.h.USER.pubkey()))]:cases.append((side+'-'+label,[(off,key)]))
cases += [('both-zero',[(139,bytes(32)),(171,bytes(32))]),('base-and-state',[(139,bytes(32))]),('quote-and-state',[(171,bytes(32))])]
def diag(r):return[re.sub(r' thrown in .*?:\d+\.', '.',s)for s in r['logs']if 'AnchorError'in s or 'Left:'in s or 'Right:'in s]
rows=[]
for name,changes in cases:
 child=copy.deepcopy(base);rec=child['bootstrap_accounts'][poolkey];blob=bytearray.fromhex(rec['data'])
 for off,key in changes:blob[off:off+32]=key
 rec['data']=blob.hex()
 if name.endswith('-and-state'):
  key=layout['groups_nearest_first'][0][2 if name.startswith('base')else 3];v=child['bootstrap_accounts'][key];b=bytearray.fromhex(v['data']);b[108]=0;v['data']=b.hex()
 assert all(v['owner']==base['bootstrap_accounts'][k]['owner']for k,v in child['bootstrap_accounts'].items())
 x=f.h.run(child);y=f.h.run(child,a.candidate);assert x['transaction_base64']==y['transaction_base64']
 for r in [x,y]:
  assert r['verified_signature_count']==2
  assert not any(' invoke ['in l and(l.startswith('Program MAyhSmz')or l.startswith('Program pAMM'))for l in r['logs'])
 diff=[k for k in ['before','after','error','events','inner','return']if x[k]!=y[k]];diff+=['diagnostics']if diag(x)!=diag(y)else[];rows.append({'case':name,'fixture':child,'original':x,'candidate':y,'different_fields':diff});print(name,x['error'],y['error'],diff,flush=True)
assert before=={str(p):sha(p)for p in inputs};d={'scope':__doc__,'inputs_sha256':before,'candidate_sha256':sha(a.candidate),'case_count':len(rows),'cases':rows,'mismatches':[r['case']for r in rows if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0));print('cases',len(rows),'mismatches',len(d['mismatches']))
