"""Signed actual2/3/4 remaining-account boost cardinality controls."""
from pathlib import Path
import argparse,base64,gzip,hashlib,importlib,inspect,json,sys
from solders.transaction import VersionedTransaction
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[];transforms={}
for route,module,kind,extra in [('legacy','pump_migrate_probe','migrate',{}),('v2_native','pump_migrate_v2_probe','migrate_v2',{}),('v2_token','pump_migrate_v2_probe','migrate_v2',{'stable':True})]:
 m=importlib.import_module(module);src=inspect.getsource(m.run);needle=' def snap():';assert src.count(needle)==1;src=src.replace(needle," if c.get('actual_remaining_count',2)>2:metas += [AccountMeta(Pubkey.default(),False,False)]*(c['actual_remaining_count']-2)\n"+needle);ns=dict(m.__dict__);exec(compile(src,str(Path(__file__)),'exec'),ns);run=ns['run'];transforms[route]=hashlib.sha256(src.encode()).hexdigest();nfixed=len(next(i for i in m.IDL['instructions']if i['name']==kind)['accounts'])
 for count in [2,3,4]:
  for enabled in [0,1]:
   for mayhem in [0,1]:
    c={'name':f'{route}_actual_count_{count}_enabled_{enabled}_mayhem_{mayhem}','boost':True,'actual_remaining_count':count,'mayhem':mayhem,'mutations':{'amm_global_config':{'patches':[[939,bytes([enabled]).hex()]]}},**extra}
    o=run(c);n=run(c,a.candidate)
    for side in [o,n]:
     tx=VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64']));assert all(tx.verify_with_results());assert len(tx.message.instructions[-1].accounts)-nfixed==count
    diff=[k for k in ['error','before','after','inner','return']if o[k]!=n[k]]
    if [l for l in o['logs']if l.startswith('Program data:')]!=[l for l in n['logs']if l.startswith('Program data:')]:diff.append('events')
    rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']],'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'transformed_fixture_sha256':transforms,'diagnostics':audit({'actual_remaining_accounts':rows})};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print('cases',len(rows),'mismatches',r['mismatches'])
