"""Signed creator-fee zero guard and predecessor error-order probes for admin CTO."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_admin_cto_differential as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[];cases=[]
for token in [False,True]:
 for fee in [0,1]:
  for same in [False,True]:
   c={'name':f'quote-token-{token}-fee-{fee}-same-{same}','current':str(h.AUTH.pubkey()),'current_writable':True,'new_creator':str(h.AUTH.pubkey()if same else h.OTHER.pubkey()),'curve_patches':[(125,fee.to_bytes(8,'little').hex()),(133,bytes(8).hex()),(32,bytes(8).hex())]}
   if token:c['quote']=str(h.Pubkey.from_bytes(bytes([88])*32))
   cases.append(c)
 for name,changes in [('authority',{'wrong_authority':True}),('new_none',{'new_none':True})]:
  c={'name':f'quote-token-{token}-pending-{name}','curve_patches':[(125,(1).to_bytes(8,'little').hex())]}|changes
  if token:c['quote']=str(h.Pubkey.from_bytes(bytes([88])*32))
  cases.append(c)
def diag(r):return[re.sub(r' thrown in .*?:\d+\.', '.',s)for s in r['logs']if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
for c in cases:
 o=h.run(c);n=h.run(c,a.candidate);assert o['signatures_verified']and n['signatures_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','before','after','events','inner','return']if o[k]!=n[k]];diff+=['diagnostics']if diag(o)!=diag(n)else[];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'case':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'case_count':len(rows),'mismatches':[x['case']['name']for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}))
