"""Signed legacy user-token program-owner gate probes with valid program-paired controls."""
from pathlib import Path
import sys,inspect,json,gzip,hashlib,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_legacy_buy_differential as buy
import pump_legacy_sell_differential as sell
for h in [buy,sell]:
 s=inspect.getsource(h.run);old="f.Pubkey.default() if spec.get('system_owner') else a.owner";assert old in s;s=s.replace(old,"(f.Pubkey.from_string(spec['owner']) if 'owner' in spec else f.Pubkey.default() if spec.get('system_owner') else a.owner)");exec(compile(s,str(Path(__file__)),'exec'),h.__dict__)
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
legacy='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA';token22='TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'
for name,h in [('buy',buy),('sell',sell)]:
 for program in ['legacy','token22']:
  for wrong in [False,True]:
   c={'name':f'{name}-{program}-wrong-owner-{wrong}','legacy_token':program=='legacy'}
   if wrong:c['account_mutations']={'associated_user':{'owner':token22 if program=='legacy' else legacy,'length':165}}
   o=h.run(c);n=h.run(c,a.candidate);diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'name':c['name'],'original_error':o['error'],'candidate_error':n['error'],'different_fields':diff,'original_entered':any('Instruction: '+name.capitalize() in l for l in o['logs'])}),flush=True)
r={'scope':__doc__,'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'mismatches':[x['case']['name'] for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0))
