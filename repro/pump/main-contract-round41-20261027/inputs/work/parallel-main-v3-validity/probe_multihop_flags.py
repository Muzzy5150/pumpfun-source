"""Signed two-curve MultiHop cashback flags through captured genuine AMM signer."""
from pathlib import Path
import sys,inspect,json,gzip,hashlib,argparse,importlib.util
R=Path(__file__).resolve().parents[2];H=R/'work/pump-tokenkeg-two-curve-recovery/ordinary_two_curve.py';sys.path.insert(0,str(R/'scripts'))
spec=importlib.util.spec_from_file_location('validity_two_curve',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
source=inspect.getsource(h.invoke).replace('candidate=None):','candidate=None,mutation=None):').replace('vm=LiteSVM().with_transaction_history(0)','vm=LiteSVM().with_transaction_history(0).with_sigverify(True)');needle=' def snapshot():';assert source.count(needle)==1;source=source.replace(needle,' if mutation:mutation(vm,metas)\n'+needle);ns=dict(h.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);invoke=ns['invoke']
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for sell in [False,True]:
 for target in ['A','B']:
  for mode in ['control','cashback','complete','complete_cashback']:
   key=h.C_A if target=='A' else h.C_B
   def mutate(vm,metas):
    ac=vm.get_account(key);d=bytearray(ac.data)
    if 'complete'in mode:d[48]=1
    if 'cashback'in mode:d[82]=1
    vm.set_account(key,h.Account(ac.lamports,bytes(d),ac.owner))
   o=invoke(sell,10**6,'exotic',1,mutation=mutate);n=invoke(sell,10**6,'exotic',1,a.candidate,mutation=mutate);assert o['verified_signature_count']==n['verified_signature_count']==1 and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','events','inner','return_data','before','after','pump_calls','token_calls']if o[k]!=n[k]];rows.append({'case':{'sell':sell,'curve':target,'mode':mode,'expected_fee_flag':1 if target=='A' else 2},'original':o,'candidate':n,'different_fields':diff});print(sell,target,mode,o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':h.sha(a.candidate),'original_sha256':h.sha(R/'evidence/original/pump/deployed.so'),'harness_sha256':h.sha(H),'script_sha256':h.sha(Path(__file__)),'transformed_invoke_sha256':hashlib.sha256(source.encode()).hexdigest(),'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows)if r['different_fields']],'cases':rows};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print('cases',len(rows),'mismatches',r['mismatches'])
