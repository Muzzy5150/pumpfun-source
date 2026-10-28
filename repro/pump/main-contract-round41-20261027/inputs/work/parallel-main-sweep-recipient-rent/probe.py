"""Signed native sweep recipient rent boundaries, with token/zero controls."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
R=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(R/'scripts'),str(R/'work/parallel-main-loader-optimized'),str(R/'work/parallel-main-v3-buyback-assert')]
import pump_captured_loader as loader
loader.install()
import pump_fee_sweep_differential as h
from solders.rent import Rent
from pump_diagnostic_audit import audit
from audit_invocations import audit_invocations

def cases():
 m=Rent.default().minimum_balance(0)
 for op in ['sweep_creator_fee','sweep_protocol_fee']:
  for native in [True,False]:
   for fee in [0,12345]:
    for balance in ([0,1,m-1,m,m+1] if native else [1,m]):
     yield {'name':f'{op}_{native}_{fee}_{balance}','op':op,'curve_quote':str(h.Pubkey.default() if native else h.STABLE),'quote':str(h.WSOL if native else h.STABLE),'creator_fee':fee,'protocol_fee':fee,'patch':{'recipient':{'lamports':balance}}}
 for op in ['sweep_creator_fee','sweep_protocol_fee']:
  for fee in [0,12345]:
   yield {'name':f'{op}_poor_payer_{fee}','op':op,'curve_quote':str(h.Pubkey.default()),'quote':str(h.WSOL),'creator_fee':fee,'protocol_fee':fee,'patch':{'recipient':{'lamports':1},'payer':{'lamports':m-1}}}

p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for c in cases():
 start=len(loader.LOADS);o=h.run(c);n=h.run(c,a.candidate);loads=loader.LOADS[start:]
 diff=[k for k in ['error','before','after'] if o[k]!=n[k]]
 diff += [k for k in ['return_data','inner_instructions'] if o['metadata'][k]!=n['metadata'][k]]
 if [l for l in o['logs'] if l.startswith('Program data: ')] != [l for l in n['logs'] if l.startswith('Program data: ')]:diff.append('events')
 assert o['signature_verification'] and n['signature_verification'] and o['transaction_base64']==n['transaction_base64']
 rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loads})
 if diff:print(json.dumps({'case':c['name'],'original':o['error'],'candidate':n['error'],'diff':diff}),flush=True)
r={'case_count':len(rows),'suites':{'sweep_rent':rows},'mismatches':[i for i,x in enumerate(rows) if x['different_fields']],'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};r['diagnostics']=audit(r['suites']);r['invocations']=audit_invocations(r);a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(r['mismatches']),'diagnostics':len(r['diagnostics']['mismatches']),'invocations':len(r['invocations']['mismatches'])}),flush=True)
