#!/usr/bin/env python3
"""Signed nested-pool comparison matrix; token-account owners and implementations stay unchanged."""
from pathlib import Path
import sys,importlib.util,copy,json,hashlib,gzip,argparse
ROOT=Path(__file__).resolve().parents[2];H=ROOT/'work/pump-nested-current21/proposed';sys.path.insert(0,str(H));sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('nested_general',H/'pump_nested_general_differential.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
DEFS=Path(__file__).with_name('cases.json');defs=json.loads(DEFS.read_text());inputs=[Path(__file__),DEFS,H/'pump_nested_general_differential.py',H/'pump_create_nested_fixture.py',H/'proposal_common.py',a.candidate,ROOT/'evidence/original/pump/deployed.so'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();hashes={str(p):sha(p)for p in inputs}
base,layout=f.fixture({'id':'pool-immediate-depth-1','depth':1,'pool_positions':[0],'pool_adjustment':0,'asymmetric':False,'expected':'success'});keys=layout['groups_nearest_first'][0];poolkey,bkey,qkey=keys[1:];rows=[]
for case in defs:
 child=copy.deepcopy(base);accounts=child['bootstrap_accounts'];m=case['mutations'];rec=accounts[poolkey];data=bytearray.fromhex(rec['data'])
 if m.get('pool_disc'):data[0]^=255
 for field,offset in [('stored_base',139),('stored_quote',171)]:
  if field in m:data[offset:offset+32]=bytes(f.h.Pubkey.from_string(m[field]))
 if 'adjustment'in m:data[245:261]=int(m['adjustment']).to_bytes(16,'little',signed=True)
 if 'pool_length'in m:data=(data+bytes(max(0,m['pool_length']-len(data))))[:m['pool_length']]
 rec['data']=data.hex()
 if 'pool_owner'in m:rec['owner']=m['pool_owner']
 for side,key in [('base',bkey),('quote',qkey)]:
  r=accounts[key];data=bytearray.fromhex(r['data'])
  if side+'_type'in m:data.extend(bytes(max(0,166-len(data))));data[165]=m[side+'_type']
  if side+'_state'in m:data[108]=m[side+'_state']
  if side+'_length'in m:data=(data+bytes(max(0,m[side+'_length']-len(data))))[:m[side+'_length']]
  r['data']=data.hex();assert r['owner']==base['bootstrap_accounts'][key]['owner']
 if m.get('pool_key'):
  replacement=m['pool_key'];accounts[replacement]=accounts.pop(poolkey);child['extra_remaining'][0]=replacement
 x=f.h.run(child);y=f.h.run(child,a.candidate);assert x['transaction_base64']==y['transaction_base64']
 for r in [x,y]:
  assert r['verified_signature_count']==2
  assert not any(' invoke ['in l and(l.startswith('Program MAyhSmz')or l.startswith('Program pAMM'))for l in r['logs'])
 diff=[k for k in ['before','after','error','events','inner','return']if x[k]!=y[k]]
 if f.logs_for_comparison(x['logs'])!=f.logs_for_comparison(y['logs']):diff.append('diagnostics')
 rows.append({'case':case,'original':x,'candidate':y,'different_fields':diff});print(case['name'],x['error'],y['error'],diff,flush=True)
assert hashes=={str(p):sha(p)for p in inputs};report={'scope':__doc__,'input_sha256':hashes,'candidate_sha256':sha(a.candidate),'case_count':len(rows),'cases':rows,'mismatches':[r['case']['name']for r in rows if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0));print('cases',len(rows),'mismatches',len(report['mismatches']))
