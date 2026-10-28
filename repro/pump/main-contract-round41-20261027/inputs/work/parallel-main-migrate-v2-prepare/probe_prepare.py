"""Signed MigrateV2 preparation order/reserved-rent boundaries for native and token quotes."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,base64,struct,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_migrate_v2_probe as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[];cases=[]
data=base64.b64decode(h.SAVED['curve']['data_base64']);rq=struct.unpack_from('<Q',data,32)[0];rent=2046240
for name,g in [('native22',{'token22':True}),('native-token',{'token22':False}),('stable-token',{'stable':True}),('stable22',{'stable':True,'quote22':True})]:
 stable=g.get('stable',False)
 variants=[('healthy',{},{}),('partial_rent',{'lamports':1000000 if stable else rq+1000000,'patches':[(125,bytes(8).hex()),(133,bytes(8).hex())]},{}),('fee_backing_missing',{'lamports':1000000 if stable else rq+rent},{}),('incomplete_low',{'lamports':1000000 if stable else rq+rent},{'complete':0}),('incomplete_overflow',{'patches':[(125,(2**64-1).to_bytes(8,'little').hex()),(133,(1).to_bytes(8,'little').hex())]},{'complete':0}),('wrong_event_low',{'lamports':1000000 if stable else rq+1000000,'patches':[(125,bytes(8).hex()),(133,bytes(8).hex())]},{'wrong':'pump_amm_event_authority'}),('wrong_event_overflow',{'patches':[(125,(2**64-1).to_bytes(8,'little').hex()),(133,(1).to_bytes(8,'little').hex())]},{'wrong':'pump_amm_event_authority'}),('already_migrated_low',{'lamports':1000000,'patches':[(i,bytes(8).hex())for i in [8,16,24,32,125,133]]},{})]
 for label,m,extra in variants:
  c={'name':name+'-'+label,'boost':True,**g,**extra}
  if m:c['mutations']={'bonding_curve':m}
  cases.append(c)
def diag(r):return[re.sub(r' thrown in .*?:\d+\.', '.',s)for s in r['logs']if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
for c in cases:
 o=h.run(c);n=h.run(c,a.candidate);assert o['signature_verification']and n['signature_verification']and o['transaction_base64']==n['transaction_base64']
 for v in [o,n]:v['events']=[s for s in v['logs']if s.startswith('Program data:')]
 diff=[k for k in ['error','before','after','events','inner','return']if o[k]!=n[k]];diff+=['diagnostics']if diag(o)!=diag(n)else[];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'case':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(h.__file__).read_bytes()).hexdigest(),'cases':rows,'case_count':len(rows),'mismatches':[x['case']['name']for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}))
