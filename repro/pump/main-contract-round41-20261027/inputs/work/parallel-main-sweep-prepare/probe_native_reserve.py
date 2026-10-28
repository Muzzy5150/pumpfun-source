"""Read-only signed sweep probes for missing native real_quote reserve in preparation."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_fee_sweep_differential as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
def diag(r):return[re.sub(r' thrown in .*?:\d+\.', '.',s)for s in r['logs']if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
for op in ['sweep_creator_fee','sweep_protocol_fee']:
 for native in [True,False]:
  for label,balance,rq,zero in [('control',10**9,0,False),('reserved',1000000,2000000,False),('zero_fees_reserved',1000000,2000000,True)]:
   c={'op':op,'name':f'{op}-native-{native}-{label}','curve_quote':str(h.Pubkey.default()if native else h.STABLE),'quote':str(h.WSOL if native else h.STABLE),'curve_lamports':balance,'patch':{'bonding_curve':{'bytes':[(32,rq.to_bytes(8,'little').hex())]}}}
   if zero:c.update(creator_fee=0,protocol_fee=0)
   o=h.run(c);n=h.run(c,a.candidate);assert o['signature_verification']and n['signature_verification']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','before','after']if o[k]!=n[k]];diff += [k for k in ['return_data','inner_instructions']if o['metadata'][k]!=n['metadata'][k]];diff += ['events']if [s for s in o['logs']if s.startswith('Program data:')]!=[s for s in n['logs']if s.startswith('Program data:')]else[];diff+=['diagnostics']if diag(o)!=diag(n)else[];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'case':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'case_count':len(rows),'mismatches':[x['case']['name']for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}))
