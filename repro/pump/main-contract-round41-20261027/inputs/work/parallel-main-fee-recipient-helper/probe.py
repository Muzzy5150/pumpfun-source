"""Signed normal/reserved recipient-list order probes, unchanged dependency programs."""
from pathlib import Path
import argparse, gzip, hashlib, importlib, json, multiprocessing, sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'work/parallel-main-loader-optimized'))
ROUTES=[('pump_legacy_buy_differential','buy',False),('pump_legacy_buy_differential','buy_exact_sol_in',False),('pump_legacy_sell_differential','sell',False)] + [(m,k,t) for m,k in [('pump_buy_v2_differential','buy_v2'),('pump_buy_v2_differential','buy_exact_quote_in_v2'),('pump_sell_v2_differential','sell_v2')] for t in [False,True]]
def init():
 import pump_captured_loader as loader
 loader.install()
def cases():
 rows=[]
 for mod,kind,token in ROUTES:
  m=importlib.import_module(mod)
  for reserved in [False,True]:
   primary=483 if reserved else 41
   array=516 if reserved else 162
   key=bytes(m.INITIAL[m.GLOBAL].data[primary:primary+32])
   for slot in range(7):
    b=[(primary+i,0) for i in range(32)]+[(array+i,0) for i in range(224)]
    b += [(array+slot*32+i,v) for i,v in enumerate(key)]
    c={'name':f'{kind}_{token}_{reserved}_isolated_slot_{slot}','kind':kind,'token_quote':token,'reserved':reserved,'account_mutations':{'global':{'bytes':b}}}
    if reserved:c['curve_bytes']=[(81,1)]
    rows.append((mod,c))
   c={'name':f'{kind}_{token}_{reserved}_primary_control','kind':kind,'token_quote':token,'reserved':reserved}
   if reserved:c['curve_bytes']=[(81,1)]
   rows.append((mod,c))
 return rows

def run(item):
 mod,c,candidate=item
 import pump_captured_loader as loader
 m=importlib.import_module(mod)
 begin=len(loader.LOADS)
 o=m.run(c);n=m.run(c,Path(candidate))
 loads=loader.LOADS[begin:]
 assert len(loads)==2
 assert o.get('signatures_verified',True) and n.get('signatures_verified',True)
 return {'case':c,'module':mod,'original':o,'candidate':n,'loader':loads,'different_fields':[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]]}

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
 init();c=cases();rows=[]
 with multiprocessing.get_context('spawn').Pool(a.workers,initializer=init) as pool:
  for r in pool.imap(run,[(m,x,str(a.candidate.resolve())) for m,x in c]):
   rows.append(r)
   if r['different_fields']:print(json.dumps({'name':r['case']['name'],'different_fields':r['different_fields'],'original_error':r['original']['error'],'candidate_error':r['candidate']['error']}),flush=True)
 from pump_diagnostic_audit import audit
 d=audit({'recipient_order':rows})
 report={'case_count':len(rows),'suites':{'recipient_order':rows},'diagnostics':d,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]}
 a.output.write_bytes(gzip.compress(json.dumps(report).encode(),mtime=0))
 print(json.dumps({'cases':len(rows),'mismatches':len(report['mismatches']),'strict_mismatches':len(d['mismatches']),'captured_loads':sum(len(r['loader']) for r in rows)}),flush=True)
 return bool(report['mismatches'] or d['mismatches'])
if __name__=='__main__':raise SystemExit(main())
