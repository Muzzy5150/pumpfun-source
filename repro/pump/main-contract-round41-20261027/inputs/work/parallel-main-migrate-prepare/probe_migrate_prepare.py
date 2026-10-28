"""Signed legacy migration preparation order and reserve-backed rent boundaries."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,base64,struct,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_migrate_probe as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
data=base64.b64decode(h.SAVED['curve']['data_base64']);rq,cf,pf=[struct.unpack_from('<Q',data,o)[0]for o in [32,125,133]];rent=2046240;total=rq+cf+pf
cases=[]
def case(name,balance=None,values=(),**extra):
 c={'name':name,'boost':True,**extra};m={}
 if balance is not None:m['lamports']=balance
 if values:m['patches']=[(o,v.to_bytes(8,'little').hex())for o,v in values]
 if m:c['mutations']={'bonding_curve':m}
 cases.append(c)
case('healthy')
case('fee_backing_missing',rq+rent)
case('partial_rent_no_fees',rq+1000000,[(125,0),(133,0)])
case('reserved_no_rent',total)
case('below_reserved',total-1)
case('below_quote_no_fees',rq-1,[(125,0),(133,0)])
case('incomplete_underfunded',rq+rent,complete=0)
case('incomplete_fee_overflow',None,[(125,2**64-1),(133,1)],complete=0)
case('already_migrated_low_rent',1000000,[(o,0)for o in [8,16,24,32,125,133]])
case('already_migrated_fees_low_rent',1000000,[(o,0)for o in [8,16,24,32]]+[(125,100),(133,200)])
case('fee_overflow',None,[(125,2**64-1),(133,1)])
case('small_creator_fee_missing',rq+rent,[(125,100),(133,0)])
def diag(r):return[re.sub(r' thrown in .*?:\d+\.', '.',s)for s in r['logs']if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
for c in cases:
 o=h.run(c);n=h.run(c,a.candidate);assert o['signature_verification']and n['signature_verification']and o['transaction_base64']==n['transaction_base64']
 for v in [o,n]:v['events']=[s for s in v['logs']if s.startswith('Program data:')]
 diff=[k for k in ['error','before','after','events','inner','return']if o[k]!=n[k]];diff+=['diagnostics']if diag(o)!=diag(n)else[];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'case':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(h.__file__).read_bytes()).hexdigest(),'cases':rows,'case_count':len(rows),'mismatches':[x['case']['name']for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}))
