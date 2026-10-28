"""Signed BuyV2/ExactV2 guard and destination-ATA order, captured dependencies."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
import buy_fixture as m
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
rows=[]
for kind in ['buy_v2','buy_exact_quote_in_v2']:
 for token in [False,True]:
  for bad in ['valid','fee_list','buyback_list','zero_buyback']:
   for label,extra in [('valid',{}),('zero_input',{'amount':0}),('zero_limit',{'minimum':0}),('complete',{'curve_bytes':[[48,1]]}),('empty_partial',{'account_mutations':{'bonding_curve':{'u64':[[24,0]]}},'trailing':[1]})]:
    c={'name':f'{kind}_{token}_{bad}_{label}','kind':kind,'token_quote':token,**extra}
    if bad=='buyback_list':c.setdefault('account_mutations',{})['global']={'bytes':[[i,0] for i in range(741,997)]}
    elif bad=='fee_list':c.setdefault('account_mutations',{})['global']={'bytes':[[i,0] for i in list(range(41,73))+list(range(162,386))]}
    elif bad=='zero_buyback':c['zero_buyback']=True
    start=len(loader.LOADS);o=m.run(c);n=m.run(c,a.candidate);loads=loader.LOADS[start:];assert len(loads)==2
    diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]]
    rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loads})
    if diff:print(json.dumps({'name':c['name'],'diff':diff,'original':o['error'],'candidate':n['error']}),flush=True)
for kind in ['buy_v2','buy_exact_quote_in_v2']:
 for absent in [['associated_quote_fee_recipient'],['associated_quote_buyback_fee_recipient'],['associated_creator_vault'],['associated_user_volume_accumulator'],['associated_quote_fee_recipient','associated_quote_buyback_fee_recipient','associated_creator_vault','associated_user_volume_accumulator']]:
  for label,extra in [('valid',{}),('zero_input',{'amount':0}),('complete',{'curve_bytes':[[48,1]]}),('bad_buyback',{'account_mutations':{'global':{'bytes':[[i,0] for i in range(741,997)]}}}),('zero_buyback',{'zero_buyback':True})]:
   c={'name':f'{kind}_{absent}_{label}','kind':kind,'token_quote':True,'absent':absent,**extra}
   start=len(loader.LOADS);o=m.run(c);n=m.run(c,a.candidate);loads=loader.LOADS[start:];assert len(loads)==2
   diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]]
   rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loads})
   if diff:print(json.dumps({'name':c['name'],'diff':diff,'original':o['error'],'candidate':n['error']}),flush=True)
d=audit({'buy_order':rows});r={'case_count':len(rows),'suites':{'buy_order':rows},'diagnostics':d,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest(),'mismatches':[i for i,x in enumerate(rows) if x['different_fields']]}
a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(r['mismatches']),'strict_mismatches':len(d['mismatches'])}),flush=True)
