"""Signed AdminCto tests of the original shared collection call boundary."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_admin_cto_differential as f
from solders.rent import Rent
from solders.transaction import VersionedTransaction
def cases():
 rent=Rent.default()
 for size in [0,8,128]:
  for amount,delta in [(0,0),(1,-1),(1,0),(1,1)]:
   required=rent.minimum_balance(size);balance=max(1,required-amount+delta)
   yield {'name':f'native-size{size}-amount{amount}-delta{delta}','current':str(f.OTHER.pubkey()),'current_writable':True,'accounts':{'current_creator':{'lamports':balance,'data':bytes(size).hex()},'creator_vault':{'lamports':rent.minimum_balance(0)+amount}}}
 for token in ['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA','TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb']:
  for frozen in [False,True]:
   yield {'name':f'token-{token[:8]}-zero-frozen{frozen}','current':str(f.OTHER.pubkey()),'current_writable':True,'quote':str(f.Pubkey.from_bytes(bytes([88])*32)),'token_program':token,'accounts':{'creator_vault_quote_token_account':{'tokens':0,'patches':[(108,'02'if frozen else'01')]}}}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();rows=[]
 for c in cases():
  o,n=f.run(c),f.run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64']
  for v in [o,n]:assert all(VersionedTransaction.from_bytes(base64.b64decode(v['transaction_base64'])).verify_with_results())
  fields=[k for k in ['before','after','error','events','inner','return']if o[k]!=n[k]]
  logs=lambda v:[s for s in v['logs']if s.startswith('Program log:')]
  rows.append({'case':c,'original':o,'candidate':n,'different_fields':fields,'program_log_difference':logs(o)!=logs(n)});print(c['name'],fields,logs(o),logs(n),flush=True)
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();report={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[r['case']['name']for r in rows if r['different_fields']or r['program_log_difference']],'inputs':{str(p):h(p)for p in [Path(__file__),Path(f.__file__),a.candidate,R/'evidence/original/pump/deployed.so']}}
 a.output.write_bytes(gzip.compress(json.dumps(report).encode(),mtime=0));print({'cases':len(rows),'mismatches':len(report['mismatches'])})
if __name__=='__main__':main()
