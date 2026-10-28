"""Signed legacy Sell rent-available boundaries with both token programs."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_legacy_sell_differential as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
def diag(r):return[re.sub(r' thrown in .*?:\d+\.', '.',s)for s in r['logs']if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
for legacy in [False,True]:
 for name,changes in [('control',[]),('quote_above_lamports',[(32,3000000)]),('fees_above_lamports',[(125,3000000)]),('sum_above_lamports',[(32,1500000),(125,1000000)]),('quote_below_lamports',[(32,1000000)]),('large_quote',[(32,10**12)])]:
  c={'name':f'sell-tokenkeg-{legacy}-{name}','legacy_token':legacy,'curve_u64':changes};o=h.run(c);n=h.run(c,a.candidate);assert o['signatures_verified'] and n['signatures_verified'] and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','events','inner','return_data']if o[k]!=n[k]];diff+=['diagnostics']if diag(o)!=diag(n)else[];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'case':c['name'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'case_count':len(rows),'mismatches':[x['case']['name']for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}))
