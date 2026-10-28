"""Signed SellV2 buyback-list validation order; fee and token dependencies unchanged."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
import sell_fixture as m
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
rows=[]
for absent in [['associated_quote_fee_recipient'],['associated_quote_buyback_fee_recipient'],['associated_creator_vault'],['associated_user_volume_accumulator'],['associated_quote_fee_recipient','associated_quote_buyback_fee_recipient','associated_creator_vault','associated_user_volume_accumulator']]:
 for label,extra in [('valid',{}),('zero',{'amount':0}),('complete',{'curve_bytes':[[48,1]]}),('bad_buyback',{'account_mutations':{'global':{'bytes':[[i,0] for i in range(741,997)]}}}),('zero_buyback',{'zero_buyback':True})]:
  c={'name':f'{absent}_{label}','token_quote':True,'absent':absent,**extra}
  start=len(loader.LOADS);o=m.run(c);n=m.run(c,a.candidate);loads=loader.LOADS[start:];assert len(loads)==2
  diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]]
  rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loads})
  if diff:print(json.dumps({'name':c['name'],'diff':diff,'original':o['error'],'candidate':n['error']}),flush=True)
d=audit({'buyback':rows});r={'case_count':len(rows),'suites':{'buyback':rows},'diagnostics':d,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'mismatches':[i for i,x in enumerate(rows) if x['different_fields']]}
a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(r['mismatches']),'strict_mismatches':len(d['mismatches'])}),flush=True)
