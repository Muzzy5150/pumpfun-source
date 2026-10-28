"""Deduplicated negative AMM-config and actual extra-account migration controls."""
from pathlib import Path
import argparse,base64,gzip,hashlib,importlib,inspect,json,sys
from solders.transaction import VersionedTransaction
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();input_path=P/'NEGATIVE-SPECS02.json';specs=json.load(open(input_path))['specs'];cache={};rows=[];transforms={}
for spec in specs:
 c=spec['case'];module='pump_migrate_probe'if c['name'].startswith('legacy')else'pump_migrate_v2_probe';m=importlib.import_module(module);extra='actual_remaining_count'in c;key=(module,extra)
 if key not in cache:
  if extra:
   source=inspect.getsource(m.run);needle=' def snap():';assert source.count(needle)==1;source=source.replace(needle," if c.get('actual_remaining_count',2)>2:metas += [AccountMeta(Pubkey.default(),False,False)]*(c['actual_remaining_count']-2)\n"+needle);ns=dict(m.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);cache[key]=ns['run'];transforms[module]=hashlib.sha256(source.encode()).hexdigest()
  else:cache[key]=m.run
 o=cache[key](c);n=cache[key](c,a.candidate);assert o['transaction_base64']==n['transaction_base64'];input_hash=hashlib.sha256((o['transaction_base64']+json.dumps({k:v for k,v in o['before'].items()if v is not None},sort_keys=True,separators=(',',':'))).encode()).hexdigest();assert input_hash==spec['input_hash']
 for side in [o,n]:
  tx=VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64']));assert all(tx.verify_with_results())
  if extra:
   kind='migrate'if module=='pump_migrate_probe'else'migrate_v2';fixed=len(next(i for i in m.IDL['instructions']if i['name']==kind)['accounts']);assert len(tx.message.instructions[-1].accounts)-fixed==c['actual_remaining_count']
 diff=[k for k in ['error','before','after','inner','return']if o[k]!=n[k]]
 if [l for l in o['logs']if l.startswith('Program data:')]!=[l for l in n['logs']if l.startswith('Program data:')]:diff.append('events')
 rows.append({'case':c,'input_hash':input_hash,'original':o,'candidate':n,'different_fields':diff})
 if diff:print(c['name'],o['error'],n['error'],diff,flush=True)
 if len(rows)%50==0:print('completed',len(rows),flush=True)
r={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']],'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_spec_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),'transformed_fixture_sha256':transforms,'diagnostics':audit({'negative_config':rows})};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print('cases',len(rows),'mismatches',r['mismatches']);assert not r['mismatches']and not r['diagnostics']['mismatches']
