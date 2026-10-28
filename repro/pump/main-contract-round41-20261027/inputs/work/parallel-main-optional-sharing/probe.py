"""Signed optional SharingConfig decoding/default probes; only SharingConfig is altered."""
from pathlib import Path
import argparse,gzip,hashlib,json,struct,sys,importlib
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
variants=[('empty',{'sharing_data_only':False}),('valid',{}),('system_owned',{'mut':{'system_owner':True}}),('wrong_discriminator',{'mut':{'bytes':[[0,0]]}})]
variants += [(f'length_{n}',{'mut':{'length':n}}) for n in [0,1,7,8,9,10,11,42,74,75,76,77,79,80,100,112,113,114]]
variants += [(f'status_{n}',{'mut':{'bytes':[[10,n]]}}) for n in [0,1,2,255]]
variants += [(f'admin_revoked_{n}',{'mut':{'bytes':[[75,n]]}}) for n in [0,1,2,255]]
variants += [(f'shares_count_{n}',{'mut':{'bytes':[[76+i,b] for i,b in enumerate(struct.pack('<I',n))]}}) for n in [0,1,2,3,10]]
variants += [(f'share_bps_{n}',{'mut':{'bytes':[[112+i,b] for i,b in enumerate(struct.pack('<H',n))]}}) for n in [0,1,10000,65535]]
variants += [('mint_zero',{'mut':{'bytes':[[11+i,0] for i in range(32)]}}),('admin_zero',{'mut':{'bytes':[[43+i,0] for i in range(32)]}})]
for module,kind in [('pump_buy_v2_differential','buy_v2'),('pump_buy_v2_differential','buy_exact_quote_in_v2'),('pump_sell_v2_differential','sell_v2')]:
 m=importlib.import_module(module)
 for token in [False,True]:
  for name,v in variants:
   c={'name':f'{kind}_{token}_{name}','kind':kind,'token_quote':token,'sharing_data_only':v.get('sharing_data_only',True)}
   if 'mut' in v:c['account_mutations']={'sharing_config':v['mut']}
   start=len(loader.LOADS);o=m.run(c);n=m.run(c,a.candidate);loads=loader.LOADS[start:];assert len(loads)==2
   diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]]
   rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loads})
   if diff:print(json.dumps({'case':c['name'],'fields':diff,'original':o['error'],'candidate':n['error']}),flush=True)
d=audit({'optional_sharing':rows});out={'case_count':len(rows),'suites':{'optional_sharing':rows},'diagnostics':d,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(out).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(out['mismatches']),'strict_mismatches':len(d['mismatches'])}),flush=True)
