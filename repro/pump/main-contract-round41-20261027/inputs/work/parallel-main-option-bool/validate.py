import argparse,base64,gzip,hashlib,json,multiprocessing,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'work/parallel-main-v2-context'))
ORIGINAL=ROOT/'evidence/original/pump/deployed.so'
def init():
 import pump_captured_loader as loader;loader.install()
 import pump_legacy_buy_differential,buy_extended,pump_v3_configured_fee_differential,pump_create_v2_differential
def cases():
 rows=[]
 tails=[[],[0],[1],[2],[255],[0,0],[0,1],[1,0],[1,1],[0,2],[0,255],[1,2],[1,255],[2,0],[255,1],[0,0,255]]
 for kind in ['buy','buy_exact_sol_in','buy_v2','buy_exact_quote_in_v2','buy_v3','buy_exact_quote_in_v3']:
  group='legacy' if kind in ['buy','buy_exact_sol_in'] else 'v3' if kind.endswith('_v3') else 'v2'
  for tail in tails:
   rows.append((group,{'name':f'{kind}_tail_{tail}','kind':kind,'operation':kind,'amount':0,'minimum':1,'max_cost':1,'trailing':tail}))
 create_args=['00'*n for n in range(12)]+['01','02','ff','00'+'00'*8+'01','00'+'00'*8+'02','00'+'00'*8+'ff','01'+'00'*8+'01']
 for arg in create_args:rows.append(('create',{'label':f'create_v2_{arg}','instruction':'create_v2','optional_args':arg}))
 return rows
def run(group,c,binary):
 if group=='legacy':
  import pump_legacy_buy_differential as f
  return f.run(c,binary),['error','accounts','events','inner','return_data']
 if group=='v2':
  import buy_extended as f
  return f.run(c,binary),['error','accounts','events','inner','return_data']
 if group=='v3':
  import pump_v3_configured_fee_differential as f
  return f.run(binary,{**c,'reserve_in':f.base_in,'reserve_out':f.base_out}),['error','accounts','event_payloads','inner_instructions','return_data']
 import pump_create_v2_differential as f
 return f.run(c,binary),['error','before','after','events','inner','return']
def execute(job):
 import pump_captured_loader as loader
 from solders.transaction import Transaction
 group,c,candidates=job;start=len(loader.LOADS);original,keys=run(group,c,ORIGINAL);assert all(Transaction.from_bytes(base64.b64decode(original['transaction_base64'])).verify_with_results());out=[]
 for name,path in candidates:
  candidate,_=run(group,c,Path(path));assert all(Transaction.from_bytes(base64.b64decode(candidate['transaction_base64'])).verify_with_results())
  out.append({'candidate_name':name,'group':group,'case':c,'original':original,'candidate':candidate,'different_fields':[k for k in keys if original[k]!=candidate[k]],'signatures_verified':True})
 loads=loader.LOADS[start:];assert len(loads)==1+len(candidates)
 return {'pairs':out,'loads':loads}
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--comparison-candidate',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();cand=[('primary',str(a.candidate.resolve()))]
 if a.comparison_candidate:cand.append(('comparison',str(a.comparison_candidate.resolve())))
 rows=[];loads=[]
 with multiprocessing.get_context('spawn').Pool(4,initializer=init) as pool:
  for result in pool.imap(execute,[(g,c,cand) for g,c in cases()]):
   rows+=result['pairs'];loads+=result['loads']
   for r in result['pairs']:
    if r['different_fields']:print(json.dumps({'name':r['case'].get('label',r['case'].get('name')),'candidate':r['candidate_name'],'different_fields':r['different_fields'],'original_error':r['original']['error'],'candidate_error':r['candidate']['error']}),flush=True)
 from pump_diagnostic_audit import audit
 d=audit({'option_bool':rows});report={'case_count':len(cases()),'pair_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'diagnostics':d,'captured_loads':loads,'candidate_sha256':{n:hashlib.sha256(Path(p).read_bytes()).hexdigest() for n,p in cand},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 a.output.write_bytes(gzip.compress(json.dumps(report).encode()));print(json.dumps({'cases':len(cases()),'pairs':len(rows),'mismatches':len(report['mismatches']),'strict_mismatches':len(d['mismatches']),'captured_loads':len(loads)}),flush=True)
if __name__=='__main__':main()
