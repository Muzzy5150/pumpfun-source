import argparse,gzip,json,multiprocessing,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
def init():
 import pump_captured_loader as l;l.install()
 import buy_fixture
def cases():
 from solders.rent import Rent
 minimum=Rent.default().minimum_balance(0);rows=[]
 for kind in ['buy_v2','buy_exact_quote_in_v2']:
  for token in [False,True]:
   for cashback in [False,True]:
    for zero_creator in [False,True]:
     for balance in [0,1,minimum-1,minimum,minimum+1]:
      c={'name':f'{kind}_{token}_{cashback}_{zero_creator}_{balance}','kind':kind,'token_quote':token,'amount':500000000,'minimum':1 if kind=='buy_exact_quote_in_v2' else 10**12,'account_mutations':{'creator_vault':{'lamports':balance}}}
      if cashback:c['curve_bytes']=[[82,1]]
      if zero_creator:c.setdefault('curve_bytes',[]).extend([[i,0] for i in range(49,81)])
      rows.append(c)
 return rows
def execute(job):
 import buy_fixture as b,pump_captured_loader as l
 c,binary=job;start=len(l.LOADS);o=b.run(c);n=b.run(c,Path(binary));loads=l.LOADS[start:];assert len(loads)==2
 return {'case':c,'original':o,'candidate':n,'different_fields':[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]],'loader':loads}
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 with multiprocessing.get_context('spawn').Pool(4,initializer=init) as pool:
  for r in pool.imap(execute,[(c,str(a.candidate.resolve())) for c in cases()]):
   rows.append(r)
   if r['different_fields']:print(json.dumps({'name':r['case']['name'],'different_fields':r['different_fields'],'original':r['original']['error'],'candidate':r['candidate']['error']}),flush=True)
 from pump_diagnostic_audit import audit
 d=audit({'rent':rows});a.output.write_bytes(gzip.compress(json.dumps({'cases':rows,'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'diagnostics':d}).encode()));print(json.dumps({'cases':len(rows),'mismatches':sum(bool(r['different_fields']) for r in rows),'strict_mismatches':len(d['mismatches'])}),flush=True)
if __name__=='__main__':main()
