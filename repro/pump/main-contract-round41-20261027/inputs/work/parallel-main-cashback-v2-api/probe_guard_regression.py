"""Strict comparison of the frozen V2 program guard witnesses, including ordinary logs."""
from pathlib import Path
import argparse,gzip,hashlib,json,re,runpy
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
ns=runpy.run_path(str(W/'probe_program_guard.py'),run_name='_guard_fixture');run=ns['run']
def logs(x):return[re.sub(r'(programs/pump/[^ :]+):\d+(?::\d+)?',r'\1:<source>',s)for s in x['logs']if not re.search(r' consumed \d+ of \d+ compute units$',s)]
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--only-new',action='store_true');a=p.parse_args();rows=[]
 for bad in [False,True]:
  if a.only_new and not bad:continue
  c={'name':'wrong-program'if bad else'token-control','v2':True,'token_quote':True,'token_balance':0,'wrong_program':bad};o=run(c);n=run(c,a.candidate)
  assert o['signatures_verified']and n['signatures_verified']and o['before']==n['before']and o['transaction_base64']==n['transaction_base64']
  diff=[k for k in ['error','accounts','events','inner','return_data']if o[k]!=n[k]]
  if logs(o)!=logs(n):diff.append('normalized_logs')
  rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff})
 report={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']],'fixture_sha256':hashlib.sha256((W/'probe_program_guard.py').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};a.output.write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0));print({'cases':len(rows),'mismatches':report['mismatches']});assert not report['mismatches']
if __name__=='__main__':main()
