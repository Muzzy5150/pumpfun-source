"""Signed legacy buyback-split boundary comparison, with unchanged account owners."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
import pump_legacy_buy_differential as buy
import pump_legacy_sell_differential as sell
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for module,kind in [(buy,'buy'),(buy,'buy_exact_sol_in'),(sell,'sell')]:
 for waived in [False,True]:
  for bps in [0,1,10000,10001,20000,2**64-1]:
   c={'name':f'{kind}_{waived}_{bps}','kind':kind,'account_mutations':{'global':{'u64':[[997,bps]]}}}
   if waived:c['account_mutations']['global']['bytes']=[[451+i,b] for i,b in enumerate(bytes(module.USER.pubkey()))]
   start=len(loader.LOADS);o=module.run(c);n=module.run(c,a.candidate);loads=loader.LOADS[start:];assert len(loads)==2
   d=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]]
   rows.append({'case':c,'original':o,'candidate':n,'different_fields':d,'loader':loads})
   if d:print(json.dumps({'case':c['name'],'diff':d,'original':o['error'],'candidate':n['error']}),flush=True)
d=audit({'legacy_buyback':rows});r={'case_count':len(rows),'suites':{'legacy_buyback':rows},'diagnostics':d,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'mismatches':[i for i,x in enumerate(rows) if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(r['mismatches']),'strict_mismatches':len(d['mismatches'])}),flush=True)
