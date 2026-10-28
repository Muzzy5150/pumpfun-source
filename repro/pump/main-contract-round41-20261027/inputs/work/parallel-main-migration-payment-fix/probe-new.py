"""Deduplicated signed migration boost policy and funding regressions."""
from pathlib import Path
import argparse,base64,gzip,hashlib,importlib,inspect,json,sys
from solders.transaction import Transaction
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();specfile=R/'work/parallel-main-migration-payment-alias/DEDUPLICATED-SPECS.json';specs=json.load(open(specfile))['specs'];cache={};transforms={};rows=[]
for spec in specs:
 c=spec['case'];module='pump_migrate_probe'if c['name'].startswith('legacy')else'pump_migrate_v2_probe';m=importlib.import_module(module);key=(module,'funded_boost_lamports'in c)
 if key not in cache:
  if key[1]:
   source=inspect.getsource(m.run);needle=' def snap():';assert source.count(needle)==1
   insert=''' if c.get('funded_boost_lamports') is not None:
  native = not c.get('stable')
  boost_key=names['boost_authority'];vault_key=names['boost_vault'];quote_key=names.get('quote_mint',names.get('wsol_mint'));balance=c['funded_boost_lamports']
  d=bytearray(165);d[:32]=bytes(quote_key);d[32:64]=bytes(boost_key);d[108]=1
  if native:
   d[64:72]=max(0,balance-2039280).to_bytes(8,'little');d[109:113]=(1).to_bytes(4,'little');d[113:121]=(2039280).to_bytes(8,'little')
  put(vault_key,Account(balance,bytes(d),qt if 'qt'in locals() else TOKEN))
'''
   source=source.replace(needle,insert+needle);ns=dict(m.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);cache[key]=ns['run'];transforms[module]=hashlib.sha256(source.encode()).hexdigest()
  else:cache[key]=m.run
 run=cache[key];o=run(c);n=run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64'];input_hash=hashlib.sha256((o['transaction_base64']+json.dumps({k:v for k,v in o['before'].items()if v is not None},sort_keys=True,separators=(',',':'))).encode()).hexdigest();assert input_hash==spec['input_hash']
 for side in [o,n]:assert all(Transaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
 diff=[k for k in ['error','before','after','inner','return']if o[k]!=n[k]]
 if [l for l in o['logs']if l.startswith('Program data:')]!=[l for l in n['logs']if l.startswith('Program data:')]:diff.append('events')
 rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'input_hash':input_hash});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']],'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_spec_sha256':hashlib.sha256(specfile.read_bytes()).hexdigest(),'transform_sha256':transforms,'diagnostics':audit({'new_migration_cases':rows})};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print('cases',len(rows),'mismatches',r['mismatches']);assert not r['mismatches']and not r['diagnostics']['mismatches']
