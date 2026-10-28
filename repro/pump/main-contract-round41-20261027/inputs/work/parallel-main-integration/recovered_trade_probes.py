"""Serial captured-loader replay of recovered bool and V2 guard counterexamples."""
from pathlib import Path
import argparse,base64,gzip,hashlib,importlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'work/parallel-main-v2-context'),str(ROOT/'work/parallel-main-v2-handlers')]
from pump_diagnostic_audit import audit
from solders.transaction import Transaction
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
def main():
 p=argparse.ArgumentParser();p.add_argument('--family',choices=['bool','v2-guard'],required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.candidate=a.candidate.resolve()
 if a.family=='bool':
  m=module('recovered_optional_bool',ROOT/'work/parallel-main-option-bool/validate.py')
  for name in ['pump_legacy_buy_differential','buy_extended','pump_v3_configured_fee_differential','pump_create_v2_differential']:importlib.import_module(name)
  jobs=m.cases();assert len(jobs)==115
 else:
  m=module('recovered_v2_guards',ROOT/'work/parallel-main-v2-handlers/guard-probe.py');f=importlib.import_module('buy_default_fixture');jobs=m.jobs();assert len(jobs)==200
 files={Path(__file__),a.candidate,ROOT/'evidence/original/pump/deployed.so'}
 for obj in list(sys.modules.values()):
  name=getattr(obj,'__file__',None)
  if name:
   file=Path(name).resolve()
   if file.is_relative_to(ROOT) and file.suffix=='.py':files.add(file)
 files.add(Path(m.__file__));before={str(f):sha(f)for f in files};rows=[]
 for i,job in enumerate(jobs):
  if a.family=='bool':
   group,c=job;o,keys=m.run(group,c,ROOT/'evidence/original/pump/deployed.so');n,_=m.run(group,c,a.candidate)
  else:
   c=job;o=f.run(c);n=f.run(c,a.candidate);keys=['error','accounts','events','inner','return_data']
  for result in [o,n]:assert all(Transaction.from_bytes(base64.b64decode(result['transaction_base64'])).verify_with_results())
  diff=[k for k in keys if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff})
  if diff:print('MISMATCH',i,diff,flush=True)
 assert before=={k:sha(k)for k in before};diag=audit({a.family:rows});out={'scope':__doc__,'family':a.family,'case_count':len(rows),'candidate_sha256':sha(a.candidate),'original_sha256':sha(ROOT/'evidence/original/pump/deployed.so'),'input_sha256':before,'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']],'diagnostics':diag};a.output.write_bytes(gzip.compress(json.dumps(out).encode(),mtime=0));print({'cases':len(rows),'mismatches':out['mismatches'],'diagnostic_mismatches':len(diag['mismatches'])});assert not out['mismatches'] and not diag['mismatches']
if __name__=='__main__':main()
