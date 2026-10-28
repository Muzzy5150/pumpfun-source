"""Signed V2 creator-vault rent boundary comparisons; balances and mode flags only."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys,importlib
from solders.rent import Rent
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[];minimum=Rent.default().minimum_balance(0);cases=[]
for mod,kind in [('pump_buy_v2_differential','buy_v2'),('pump_buy_v2_differential','buy_exact_quote_in_v2'),('pump_sell_v2_differential','sell_v2')]:
 for token in [False,True]:
  for mode in ['creator','zero_creator','cashback']:
   for balance in [0,1,minimum-1,minimum,minimum+1]:
    c={'name':f'{kind}_{token}_{mode}_vault_{balance}','kind':kind,'token_quote':token,'account_mutations':{'creator_vault':{'lamports':balance}}}
    if mode=='zero_creator':c['curve_bytes']=[[49+i,0] for i in range(32)]
    if mode=='cashback':c['curve_bytes']=[[82,1]]
    cases.append((mod,c))
  for payer in [50000,minimum-1,minimum+5000]:
   c={'name':f'{kind}_{token}_poor_payer_{payer}','kind':kind,'token_quote':token,'account_mutations':{'creator_vault':{'lamports':0},'user':{'lamports':payer}}}
   if kind=='buy_exact_quote_in_v2':c['amount']=10000
   cases.append((mod,c))
for module,c in cases:
 m=importlib.import_module(module);start=len(loader.LOADS);o=m.run(c);n=m.run(c,a.candidate);ls=loader.LOADS[start:];assert len(ls)==2;diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];rows.append({'case':c,'module':module,'original':o,'candidate':n,'different_fields':diff,'loader':ls})
 if diff:print(json.dumps({'case':c['name'],'fields':diff,'original_error':o['error'],'candidate_error':n['error']}),flush=True)
d=audit({'v2_vault_rent':rows});out={'case_count':len(rows),'suites':{'v2_vault_rent':rows},'diagnostics':d,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'minimum_balance':minimum,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(out).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(out['mismatches']),'strict_mismatches':len(d['mismatches'])}),flush=True)
