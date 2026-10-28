"""Read-only signed V3 fee-waiver probes, patching only fixture Global data in memory."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
def run(c,binary,offset):
 old=h.initial[h.global_key]
 try:
  if offset is not None:
   data=bytearray(old.data);data[offset:offset+32]=bytes(h.user.pubkey());h.initial[h.global_key]=h.f.Account(old.lamports,bytes(data),old.owner)
  return h.run(binary,c)
 finally:h.initial[h.global_key]=old
def diag(r):return [re.sub(r' thrown in .*?:\d+\.', '.',s) for s in r['logs'] if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
for op in ['buy_v3','buy_exact_quote_in_v3','sell_v3']:
 for token in [False,True]:
  for mode,offset in [('control',None),('whitelist_user',451),('adjacent_admin_user',418)]:
   c={'name':f'{op}-token-{token}-{mode}','operation':op,'reserve_in':h.base_in,'reserve_out':h.base_out,'amount':500000000 if op=='sell_v3' else 10**9,'max_cost':10**12 if op=='buy_v3' else 0 if op=='sell_v3' else 1,'user_lamports':10**16,'token_quote':token,'replace':13}
   o=run(c,R/'evidence/original/pump/deployed.so',offset);n=run(c,a.candidate,offset);assert o['signature_verified'] and n['signature_verified'] and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','event_payloads','inner_instructions','return_data'] if o[k]!=n[k]];diff+=['diagnostics'] if diag(o)!=diag(n) else [];rows.append({'route':op,'mode':mode,'global_data_offset':offset,'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'case':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'case_count':len(rows),'mismatches':[x['case']['name'] for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}))
