"""Signed negative AMM GlobalConfig metadata and migration boost-gate coverage."""
from pathlib import Path
import argparse,gzip,hashlib,importlib,json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
mutations=[('control',{}),('owner_system',{'owner':'11111111111111111111111111111111'}),('owner_pump',{'owner':'6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'}),('owner_token',{'owner':'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'}),('bad_discriminator',{'patches':[[0,bytes(8).hex()]]})]
mutations += [(f'length_{n}',{'length':n})for n in [0,7,8,906,907,908,938,939,940,941,948]]
mutations += [(f'bool_{offset}_{value}',{'patches':[[offset,bytes([value]).hex()]]})for offset,value in [(417,2),(417,255),(642,2),(939,0),(939,2),(939,255),(940,2),(940,255)]]
mutations += [('extra_zero',{'patches':[[949,'00']]}),('extra_nonzero',{'patches':[[949,'ff']]}),('extra_32',{'patches':[[949,(bytes([117])*32).hex()]]})]
for route,module,extra in [('legacy','pump_migrate_probe',{}),('v2_native','pump_migrate_v2_probe',{}),('v2_token','pump_migrate_v2_probe',{'stable':True})]:
 m=importlib.import_module(module)
 for count in [0,1,2]:
  for mayhem in [0,1]:
   for label,mutation in mutations:
    c={'name':f'{route}_{count}_{mayhem}_{label}','boost':True,'remaining_count':count,'mayhem':mayhem,'mutations':{'amm_global_config':mutation},**extra}
    o=m.run(c);n=m.run(c,a.candidate);diff=[k for k in ['error','before','after','inner','return']if o[k]!=n[k]]
    if [l for l in o['logs']if l.startswith('Program data:')]!=[l for l in n['logs']if l.startswith('Program data:')]:diff.append('events')
    rows.append({'case':c,'variant':label,'original':o,'candidate':n,'different_fields':diff})
    if diff:print(c['name'],o['error'],n['error'],diff,flush=True)
   print(route,count,mayhem,'done',flush=True)
r={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']],'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'diagnostics':audit({'negative_amm_config':rows})};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print('cases',len(rows),'mismatches',r['mismatches'])
