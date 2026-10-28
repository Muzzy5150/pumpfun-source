import argparse,gzip,json,sys,multiprocessing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
def init():
 import pump_captured_loader as loader;loader.install()
 import buy_default_fixture
def jobs():
 rows=[]
 for kind in ['buy_v2','buy_exact_quote_in_v2']:
  for token in [False,True]:
   for partial in [False,True]:
    for scenario in ['ordinary','zero_input','zero_minimum','complete','empty_reserves']:
     for recipients in ['good','bad_fee','bad_buyback','both_bad','default_buyback']:
      c={'name':f'{kind}_{token}_{partial}_{scenario}_{recipients}','kind':kind,'token_quote':token,'trailing':[int(partial)],'amount':500000000}
      if kind=='buy_exact_quote_in_v2':c['minimum']=1
      if scenario=='zero_input':c['amount']=0
      if scenario=='zero_minimum':c['minimum']=0
      if scenario=='complete':c['curve_bytes']=[[48,1]]
      if scenario=='empty_reserves':c.setdefault('account_mutations',{})['bonding_curve']={'u64':[[24,0]]}
      edits=[]
      if recipients in ['bad_fee','both_bad']:edits += [[i,0] for i in range(41,73)]+[[i,0] for i in range(162,386)]
      if recipients in ['bad_buyback','both_bad']:edits += [[i,0] for i in range(741,997)]
      if edits:c.setdefault('account_mutations',{})['global']={'bytes':edits}
      if recipients=='default_buyback':c['default_buyback']=True
      rows.append(c)
 return rows
def execute(item):
 import buy_default_fixture as b,pump_captured_loader as loader
 c,candidate=item;start=len(loader.LOADS);o=b.run(c);n=b.run(c,Path(candidate));loads=loader.LOADS[start:];assert len(loads)==2
 return {'case':c,'original':o,'candidate':n,'different_fields':[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]],'loader':loads}
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 with multiprocessing.get_context('spawn').Pool(4,initializer=init) as pool:
  for r in pool.imap(execute,[(c,str(a.candidate.resolve())) for c in jobs()]):
   rows.append(r)
   if r['different_fields']:print(json.dumps({'name':r['case']['name'],'different_fields':r['different_fields'],'original':r['original']['error'],'candidate':r['candidate']['error']}),flush=True)
 from pump_diagnostic_audit import audit
 d=audit({'v2':rows});report={'cases':rows,'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'diagnostics':d};a.output.write_bytes(gzip.compress(json.dumps(report).encode()));print(json.dumps({'cases':len(rows),'mismatches':len(report['mismatches']),'strict_mismatches':len(d['mismatches'])}),flush=True)
if __name__=='__main__':main()
