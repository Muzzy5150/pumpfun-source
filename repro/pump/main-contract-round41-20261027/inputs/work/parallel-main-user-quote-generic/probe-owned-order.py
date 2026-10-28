"""Signed creator/cashback zero-fee and split-failure order controls."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
import pump_buy_v2_differential as m
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for kind in ['buy_v2','buy_exact_quote_in_v2']:
 for quote in ['native','token','token22']:
  for cashback in [False,True]:
   for zero_creator in [False,True]:
    for bps in [0,20000]:
     case={'name':f'{kind}_{quote}_cashback_{cashback}_zero_creator_{zero_creator}_buyback_{bps}','kind':kind,'token_quote':quote!='native','token22':quote=='token22','account_mutations':{'global':{'u64':[[997,bps]]}}}
     if cashback:case['curve_bytes']=[[82,1]]
     if zero_creator:case.setdefault('curve_bytes',[]).extend([[49+i,0]for i in range(32)])
     start=len(loader.LOADS);o=m.run(case);n=m.run(case,a.candidate);loads=loader.LOADS[start:];assert len(loads)==2
     bad=[k for k in ['error','accounts','events','inner','return_data']if o[k]!=n[k]]
     rows.append({'case':case,'original':o,'candidate':n,'different_fields':bad,'loader':loads})
     if bad:print(json.dumps({'case':case['name'],'different_fields':bad,'original':o['error'],'candidate':n['error']}),flush=True)
r={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']],'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'diagnostics':audit({'owned_order':rows})}
a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(r['mismatches']),'diagnostic_mismatches':len(r['diagnostics']['mismatches'])}),flush=True)
if r['mismatches']or r['diagnostics']['mismatches']:raise SystemExit(1)
