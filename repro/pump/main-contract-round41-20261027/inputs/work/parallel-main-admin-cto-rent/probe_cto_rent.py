"""Signed admin CTO native-reserved rent probes with token-quote controls."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_admin_cto_differential as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
def diag(r):return[re.sub(r' thrown in .*?:\d+\.', '.',s)for s in r['logs']if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
variants=[('control',10**9,[]),('low_no_reserve',10**6,[(32,0),(125,0),(133,0)]),('low_native_reserve',10**6,[(32,500000),(125,100000),(133,200000)]),('rent_full_reserved',2100000,[(32,2000000),(125,0),(133,0)]),('reserve_exceeds_balance',10**6,[(32,3000000),(125,0),(133,0)]),('reserve_overflow',10**6,[(32,0),(125,2**64-1),(133,1)])]
for token in [False,True]:
 for name,balance,values in variants:
  c={'name':('token-'if token else'native-')+name,'accounts':{'bonding_curve':{'lamports':balance}},'curve_patches':[(i,v.to_bytes(8,'little').hex())for i,v in values]}
  if token:c['quote']=str(h.Pubkey.from_bytes(bytes([88])*32))
  o=h.run(c);n=h.run(c,a.candidate);assert o['signatures_verified']and n['signatures_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','before','after','events','inner','return']if o[k]!=n[k]];diff+=['diagnostics']if diag(o)!=diag(n)else[];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'case':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'case_count':len(rows),'mismatches':[x['case']['name']for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}))
