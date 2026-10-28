"""Read-only signed fee-waiver probes; no source mutation or new program build."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_legacy_buy_differential as lb
import pump_legacy_sell_differential as ls
import pump_buy_v2_differential as vb
import pump_sell_v2_differential as vs
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
def diag(r):return [re.sub(r' thrown in .*?:\d+\.', '.',s) for s in r['logs'] if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
routes=[('buy',lb,{}),('buy_exact_sol_in',lb,{'minimum':1}),('sell',ls,{}),('buy_v2',vb,{}),('buy_exact_quote_in_v2',vb,{'minimum':1}),('sell_v2',vs,{})]
for op,h,extras in routes:
 for token in ([False,True] if '_v2' in op else [False]):
  for mode,offset in [('control',None),('whitelist_user',451),('adjacent_admin_user',419)]:
   c={'name':f'{op}-token-{token}-{mode}','kind':op,'token_quote':token,**extras}
   if offset is not None:c['account_mutations']={'global':{'bytes':[(offset+i,v) for i,v in enumerate(bytes(h.USER.pubkey()))]}}
   o=h.run(c);n=h.run(c,a.candidate);assert o['signatures_verified'] and n['signatures_verified'] and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];diff += ['diagnostics'] if diag(o)!=diag(n) else [];rows.append({'route':op,'mode':mode,'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'case':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'case_count':len(rows),'mismatches':[x['case']['name'] for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}))
