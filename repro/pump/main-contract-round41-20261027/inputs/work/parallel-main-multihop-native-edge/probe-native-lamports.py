"""Signed native MultiHop input bounds through the captured AMM caller."""
from pathlib import Path
import argparse,base64,gzip,hashlib,importlib.util,json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
H=R/'repro/pump/native-curve-partial-fortyeight/harness/pump_multi_hop_curve_differential.py';spec=importlib.util.spec_from_file_location('native_edge_fixture',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
from solders.transaction import Transaction
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for amount in [0,10**6,10**9]:
 for balance in [None,2**64-1,2**64-2]:
  def mutation(vm,metas):
   if balance is not None:
    key=metas[18].pubkey;account=vm.vm.get_account(key);vm.vm.set_account(key,h.h.Account(balance,account.data,account.owner))
  start=len(loader.LOADS);o=h.invoke(False,amount,mutation=mutation);n=h.invoke(False,amount,a.candidate,mutation);loads=loader.LOADS[start:]
  for side in [o,n]:
   tx=Transaction.from_bytes(base64.b64decode(side['transaction_base64']));assert all(tx.verify_with_results());side['signatures_verified']=True
  assert o['transaction_base64']==n['transaction_base64'];bad=h.compare(o,n)
  rows.append({'case':{'amount':amount,'curve_lamports':balance},'original':o,'candidate':n,'mismatches':bad,'loader':loads})
  print(amount,balance,o['error'],n['error'],bad,flush=True)
r={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[i for i,row in enumerate(rows)if row['mismatches']],'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(H.read_bytes()).hexdigest()};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));assert not r['mismatches']
