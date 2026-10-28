import argparse,concurrent.futures,gzip,hashlib,json,multiprocessing,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from pump_diagnostic_audit import audit

def init():
 import pump_captured_loader
 pump_captured_loader.install()

def execute(item):
 import pump_admin_cto_differential as f
 c,candidate=item;o=f.run(c);n=f.run(c,candidate)
 assert o['signatures_verified'] and n['signatures_verified']
 diff=[k for k in ['error','before','after','events','inner','return'] if o[k]!=n[k]];ls=[]
 return {'case':c,'original':o,'candidate':n,'different_fields':diff},ls

def main():
 import pump_admin_cto_differential as f
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=2);p.add_argument('--only-extra',action='store_true');a=p.parse_args()
 cases=f.cases()
 frozen=[]
 for filename in ['freeze.json.gz','edges.json.gz']:
  path=ROOT/'work/parallel-main-cto-frozen'/filename;frozen.append(path)
  r=json.loads(gzip.decompress(path.read_bytes()));cases += [row['case'] for row in r['cases']]
 base_count=len(cases)
 for name in ['current_creator','creator_vault','holder_creator_vault','event_authority','program']:
  cases += [dict(name='owned-wrong-readonly-'+name,wrong=name,readonly=['bonding_curve']),dict(name='owned-wrong-missing-program-'+name,wrong=name,count=25),dict(name='owned-wrong-no-new-'+name,wrong=name,new_none=True)]
 cases += [dict(name='owned-global-first',global_patches=[(0,'ff')],wrong='creator_vault'),dict(name='owned-curve-first',curve_patches=[(0,'ff')],wrong='holder_creator_vault'),dict(name='owned-quote-first',accounts={'quote_mint':{'length':0}},wrong='program'),dict(name='owned-short-unsigned',count=24,unsigned=True),dict(name='owned-short-holder-invalid',count=24,holder=True,new_none=False),dict(name='owned-last-program-unsigned',wrong='program',unsigned=True),dict(name='owned-event-with-bad-bool',wrong='event_authority',curve_patches=[(124,'02')])]
 for row in json.loads(gzip.decompress((ROOT/'work/parallel-main-cto-context/token-owner-before.json.gz').read_bytes()))['cases']:cases.append(row['case'])
 for token,owner in [(str(f.TOKEN),'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'),('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',str(f.TOKEN))]:
  cases += [dict(name='quote-and-owner-mismatch-'+token,token_program=token,curve_patches=[(83,bytes([88]*32).hex())],accounts={'quote_mint':{'owner':owner}}),dict(name='decode-before-owner-'+token,token_program=token,accounts={'quote_mint':{'owner':owner,'length':0}})]
 cases=cases[base_count:]
 assert len(cases)==34,len(cases)
 paths=[Path(__file__),a.candidate,Path(f.__file__),ROOT/'scripts/pump_captured_loader.py',ROOT/'evidence/original/pump/deployed.so',ROOT/'evidence/original/pump_fees/deployed.so',ROOT/'evidence/original/pump_amm/deployed.so',ROOT/'evidence/original/pump/program-account.bin',ROOT/'evidence/original/pump/programdata-account.bin',*frozen,ROOT/'work/parallel-main-cto-context/token-owner-before.json.gz']
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(p):sha(p) for p in paths};rows=[];loads=[]
 # The outer captured-loader wrapper owns all loads in this process.
 for i,(row,ls) in enumerate(map(execute,[(c,str(a.candidate.resolve())) for c in cases])):
  rows.append(row)
  if row['different_fields']:print('MISMATCH',i,json.dumps(row['case']),row['different_fields'],flush=True)
 assert before=={str(p):sha(p) for p in paths};diag=audit({'cto':rows});r={'scope':'Normally signed main-Pump AdminCto execution with captured upgradeable main loader and original dependencies. Full state/event/CPI/return comparison plus strict Anchor diagnostics; no full ELF identity claim.','case_count':len(rows),'cases':rows,'provenance':before,'loader_loads':loads,'diagnostics':diag,'mismatches':[i for i,row in enumerate(rows) if row['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode()));a.output.with_suffix('.diagnostics.json').write_text(json.dumps(diag,indent=2)+'\n');print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches'],'diagnostics':len(diag['mismatches']),'loader_loads':len(loads)}),flush=True);return bool(r['mismatches'] or diag['mismatches'])
if __name__=='__main__':raise SystemExit(main())
