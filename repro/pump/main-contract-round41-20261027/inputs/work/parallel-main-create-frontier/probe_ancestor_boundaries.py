"""Signed main-Pump nested creation with synthetic truncated ancestor account data."""
from pathlib import Path
import argparse,base64,copy,gzip,hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from solders.transaction import Transaction
from pump_diagnostic_audit import audit
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def cases(original):
 lengths=sorted({0,1,7,8,*[8+n+d for n in [41,73,74,75,107,116,117,133,158]for d in [-1,0,1]],166,167,200})
 for n in lengths:yield {'name':f'account_length_{n}','data':original[:n]+bytes(max(0,n-len(original)))}
 for offset in [48,81,82,123,124]:
  for value in [0,1,2,255]:
   for n in sorted({min(166,offset+1),166}):
    b=bytearray(original[:n]);b[offset]=value
    yield {'name':f'bool_{offset}_{value}_length_{n}','data':bytes(b)}
 for off in [0,7]:
  b=bytearray(original);b[off]^=1;yield {'name':f'discriminator_{off}','data':bytes(b)}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 f=module('frontier_nested',ROOT/'scripts/pump_create_nested_differential.py');h=f.load();boot,child=f.prepare({})
 key=str(h.Pubkey.find_program_address([b'bonding-curve',bytes(h.OTHER.pubkey())],h.PROGRAM)[0]);original=bytes.fromhex(child['bootstrap_accounts'][key]['data'])
 files=[Path(__file__),Path(f.__file__),Path(h.__file__),a.candidate,ROOT/'evidence/original/pump/deployed.so',ROOT/'scripts/pump_diagnostic_audit.py'];before={str(x.resolve()):sha(x)for x in files}
 rows=[]
 for c in cases(original):
  fixture=copy.deepcopy(child);fixture['bootstrap_accounts'][key]['data']=c['data'].hex()
  o=h.run(fixture);n=h.run(fixture,a.candidate)
  for result in [o,n]:assert all(Transaction.from_bytes(base64.b64decode(result['transaction_base64'])).verify_with_results())
  diff=[k for k in ['before','after','error','events','inner','return']if o[k]!=n[k]]
  rows.append({'case':{k:v for k,v in c.items()if k!='data'}|{'ancestor_data':c['data'].hex()},'original':o,'candidate':n,'different_fields':diff})
  if diff:print('MISMATCH',c['name'],diff,flush=True)
 diag=audit({'ancestor_boundaries':rows});assert before=={k:sha(k)for k in before};r={'scope':__doc__,'original_sha256':sha(ROOT/'evidence/original/pump/deployed.so'),'candidate_sha256':sha(a.candidate),'input_sha256':before,'bootstrap':boot,'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']],'diagnostics':diag}
 a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));print({'cases':len(rows),'mismatches':r['mismatches'],'diagnostic_mismatches':len(diag['mismatches'])},flush=True);assert not r['mismatches'] and not diag['mismatches']
if __name__=='__main__':main()
