"""Signed IDL transfer-with-seed order and amount boundary controls."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,re,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_idl_authority_differential as f
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction

def cases():
 for amount in [0,1,890880,2**64-1]:
  for writable in [False,True]:
   for length in [0,1]:
    yield {'name':f'system-amount{amount}-write{writable}-length{length}','writable':'authority'if writable else None,'mutations':{'idl_account':{'owner':str(f.Pubkey.default()),'lamports':amount,'length':length}}}
 for amount in [0,1,2]:
  for authority in [2**64-2,2**64-1]:
   yield {'name':f'recipient-overflow-amount{amount}-authority{authority}','writable':'authority','mutations':{'idl_account':{'owner':str(f.Pubkey.default()),'lamports':amount,'length':0},'authority':{'lamports':authority}}}
 for size in [8,44,81,20000]:
  yield {'name':f'pump-bad-disc-realloc-size{size}','mutations':{'idl_account':{'length':size,'patches':[(0,'ff')]}}}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();rows=[]
 for c in cases():
  o,n=f.run(c),f.run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64']
  for side in [o,n]:assert all(VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
  diff=[k for k in ['before','after','error','events','inner','return']if o[k]!=n[k]]
  seq=lambda x:[l for l in x['logs']if re.match(r'^Program [1-9A-HJ-NP-Za-km-z]+ (?:invoke \[|success$|failed:)',l)]
  if seq(o)!=seq(n):diff.append('invocations')
  rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
 diag=audit({'idl_transfer':rows});h=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();r={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[x['case']['name']for x in rows if x['different_fields']],'diagnostics':diag,'candidate_sha256':h(a.candidate),'script_sha256':h(Path(__file__)),'fixture_sha256':h(Path(f.__file__))};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print({'cases':len(rows),'mismatches':len(r['mismatches']),'diagnostic_mismatches':len(diag['mismatches'])})
if __name__=='__main__':main()
