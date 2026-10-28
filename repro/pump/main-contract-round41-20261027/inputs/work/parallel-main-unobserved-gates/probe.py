"""Signed private probes for previously unobserved main-Pump guards."""
from pathlib import Path
import argparse,base64,gzip,hashlib,importlib,json,re,struct,sys
from solders.transaction import VersionedTransaction
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;sys.path[:0]=[str(P),str(R/'scripts'),str(R/'work/parallel-main-loader-optimized')]
import pump_captured_loader as loader
loader.install()
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--family',choices=['cashback_accounts','cto_cashback_fee','mayhem_create'],required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();cases=[]
if a.family=='cashback_accounts':
 h=importlib.import_module('pump_legacy_sell_differential');fields=['error','accounts','before','events','inner','return_data']
 for token in [False,True]:
  for label,args in [('full',{'cashback_account':True}),('none',{'remaining':False}),('uva_only',{'cashback_account':True,'remaining':False}),('v2_only',{'omit_buyback':True}),('uva_v2',{'cashback_account':True,'omit_buyback':True})]:
   cases.append({'name':f'cashback_{token}_{label}','legacy_token':token,'curve_bytes':[[82,1]],**args})
  for label,args in [('zero',{'amount':0}),('complete',{'curve_bytes':[[82,1],[48,1]]}),('slippage',{'minimum':2**64-1}),('recipient',{'wrong_keys':['fee_recipient']})]:cases.append({'name':f'precedence_{token}_{label}','legacy_token':token,'remaining':False,'curve_bytes':[[82,1]],**args})
  cases += [{'name':f'ordinary_{token}','legacy_token':token},{'name':f'ordinary_no_remaining_{token}','legacy_token':token,'remaining':False}]
elif a.family=='cto_cashback_fee':
 h=importlib.import_module('pump_admin_cto_differential');fields=['error','before','after','events','inner','return'];quote=str(h.Pubkey(bytes([88])*32));enabled=[(1045,'01'),(1046,struct.pack('<Q',10000).hex())]
 for fee in [None,0,1,10001]:
  for cashback in [False,True]:
   c={'name':f'exotic_cashback_{cashback}_fee_{fee}','quote':quote,'global_patches':enabled,'curve_patches':[(82,'01'if cashback else'00')]}
   if fee is not None:c['fee']=fee
   cases.append(c)
 base={'quote':quote,'fee':1,'global_patches':enabled,'curve_patches':[(82,'01')]}
 cases += [dict(base,name='precedence_fee_config_disabled',global_patches=[(1045,'00')]),dict(base,name='precedence_native_quote',quote=str(h.Pubkey.default())),dict(base,name='precedence_new_none',new_none=True),dict(base,name='precedence_mayhem',curve_patches=[(82,'01'),(81,'01')]),dict(base,name='precedence_bad_authority',wrong_authority=True),dict(base,name='holder_overrides_cashback',holder=True,new_none=True,global_patches=enabled+[(1086,'01')])]
else:
 h=importlib.import_module('create_fixture');fields=['error','before','after','events','inner','return']
 for mode in [False,True]:
  for enabled in [False,True]:
   for quote in [False,True]:cases.append({'case':f'mayhem_{mode}_enabled_{enabled}_quote_{quote}','instruction':'create_v2','is_mayhem_mode':mode,'quote':quote,'global_patches':[(450,'01'),(515,'01'if enabled else'00')]})
 base={'instruction':'create_v2','is_mayhem_mode':True,'global_patches':[(450,'01'),(515,'00')]}
 cases += [dict(base,case='precedence_create_disabled',global_patches=[(450,'00'),(515,'00')]),dict(base,case='precedence_cashback',optional_args='01'),dict(base,case='precedence_zero_creator',creator=str(h.Pubkey.default())),dict(base,case='precedence_long_name',name='x'*33),dict(base,case='precedence_short_accounts',account_count=5)]
rows=[];txs=0
for c in cases:
 start=len(loader.LOADS);o=h.run(c);n=h.run(c,a.candidate);loads=loader.LOADS[start:];assert len(loads)==2
 for result in [o,n]:
  tx=VersionedTransaction.from_bytes(base64.b64decode(result['transaction_base64']));assert all(tx.verify_with_results())and len(tx.signatures)==tx.message.header.num_required_signatures;txs+=1
 assert o['transaction_base64']==n['transaction_base64']
 diff=[k for k in fields if o[k]!=n[k]]
 inv=lambda x:[s for s in x['logs']if re.match(r'^Program \S+ invoke \[\d+\]$',s)]
 if inv(o)!=inv(n):diff.append('invocation_order')
 rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loads});print(json.dumps({'case':c.get('name',c.get('case')),'original':o['error'],'candidate':n['error'],'diff':diff}),flush=True)
diag=audit({a.family:rows});out={'family':a.family,'case_count':len(rows),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'suites':{a.family:rows},'diagnostics':diag,'verified_transactions':txs,'mismatches':[i for i,x in enumerate(rows)if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(out).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(out['mismatches']),'strict_mismatches':len(diag['mismatches'])}),flush=True)
