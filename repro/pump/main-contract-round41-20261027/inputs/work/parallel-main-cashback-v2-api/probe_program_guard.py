"""ClaimCashbackV2 program-ID guard: typed owners unchanged, parser-derived addresses."""
from pathlib import Path
import argparse,base64,gzip,hashlib,inspect,json,sys
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'))
import pump_cashback_differential as h
source=inspect.getsource(h.run)
needle=" ix=IX['claim_cashback_v2' if c.get('v2') else 'claim_cashback'];metas="
assert source.count(needle)==1
source=source.replace(needle,''' if c.get('wrong_program'):
  old_source=vm.get_account(keys['associated_user_volume_accumulator']);old_destination=vm.get_account(keys['associated_quote_user'])
  keys['quote_token_program']=f.Pubkey.default()
  keys['associated_user_volume_accumulator']=f.Pubkey.find_program_address([bytes(vol),bytes(keys['quote_token_program']),bytes(mint)],ATA)[0]
  keys['associated_quote_user']=f.Pubkey.find_program_address([bytes(user),bytes(keys['quote_token_program']),bytes(mint)],ATA)[0]
  vm.set_account(keys['associated_user_volume_accumulator'],old_source)
  vm.set_account(keys['associated_quote_user'],old_destination)
  assert vm.get_account(mint).owner==tp
  assert vm.get_account(keys['associated_user_volume_accumulator']).owner==tp
  assert vm.get_account(keys['associated_quote_user']).owner==tp
'''+needle)
needle=' tx=f.Transaction.new_signed_with_payer('
assert source.count(needle)==1
source=source.replace(needle," before={str(k):{'lamports':a.lamports,'owner':str(a.owner),'data_hex':a.data.hex(),'executable':a.executable}for k in {m.pubkey for m in metas}if k!=P and (a:=vm.get_account(k))is not None}\n"+needle)
source=source.replace(" return {'error':"," return {'before':before,'error':")
ns=dict(h.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);run=ns['run']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();rows=[]
 for bad in [False,True]:
  c={'name':'wrong-program'if bad else'token-control','v2':True,'token_quote':True,'token_balance':0,'wrong_program':bad}
  o=run(c);n=run(c,a.candidate);assert o['signatures_verified']and n['signatures_verified']and o['transaction_base64']==n['transaction_base64']and o['before']==n['before']
  fields=[k for k in ['error','accounts','events','inner','return_data','logs']if o[k]!=n[k]]
  rows.append({'case':c,'original':o,'candidate':n,'different_fields':fields});print(json.dumps({'case':c['name'],'original_error':o['error'],'candidate_error':n['error'],'differences':fields,'original_logs':o['logs'],'candidate_logs':n['logs']}),flush=True)
 report={'scope':__doc__,'case_count':len(rows),'cases':rows,'original_sha256':h.hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'candidate_sha256':h.hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'source_harness_sha256':h.hashlib.sha256(Path(h.__file__).read_bytes()).hexdigest(),'transformed_source_sha256':h.hashlib.sha256(source.encode()).hexdigest(),'script_sha256':h.hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'limits':['Wrong program is an existing System Program account; no owner/executable is changed.','Token accounts are copied with preserved data/owners to addresses derived by the unchecked context seeds.','Synthetic parser-admitted states; no historical creation reachability claim.']}
 a.output.write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
