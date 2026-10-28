from pathlib import Path
import sys,importlib.util,argparse,json,gzip,struct,hashlib
W=Path(__file__).resolve().parent;R=W.parents[1]
p=R/'repro/pump/native-curve-partial-fortyeight/harness/pump_multi_hop_curve_differential.py';spec=importlib.util.spec_from_file_location('native_base',p);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

def mutation(c):
 def apply(vm,metas):
  key=metas[18].pubkey;ac=vm.vm.get_account(key);d=bytearray(ac.data);struct.pack_into('<Q',d,24,c['cap']);struct.pack_into('<Q',d,32,0 if c.get('zero_pool') else 27960);vm.vm.set_account(key,h.h.Account(ac.lamports,bytes(d),ac.owner))
  key=metas[13].pubkey;ac=vm.vm.get_account(key);d=bytearray(ac.data);struct.pack_into('<Q',d,146,c.get('migration_fee',1 if c.get('zero_pool') else 0));vm.vm.set_account(key,h.h.Account(ac.lamports,bytes(d),ac.owner))
  if 'vault_amount' in c:
   key=metas[19].pubkey;ac=vm.vm.get_account(key);d=bytearray(ac.data);struct.pack_into('<Q',d,64,c['vault_amount']);vm.vm.set_account(key,h.h.Account(ac.lamports,bytes(d),ac.owner))
  key=metas[14].pubkey;ac=vm.vm.get_account(key);fee=struct.pack('<QQQ',0,*c['fees']);d=ac.data[:41]+fee+struct.pack('<I',1)+bytes(16)+fee+struct.pack('<I',0)+fee;vm.vm.set_account(key,h.h.Account(ac.lamports,d.ljust(4097,bytes([0])),ac.owner))
 return apply

def cases():
 for pb,cb in [(95,30),(0,0),(5000,5000),(10000,10000)]:
  for amount in [4,5,6,7,10,1000,10**9]:
   for zero in [False,True]:yield {'name':f'p{pb}_c{cb}_a{amount}_zero{zero}','fees':[pb,cb],'amount':amount,'cap':0,'zero_pool':zero}
 for fee in [0,1,2]:yield {'name':f'empty_pool_{fee}','fees':[95,30],'amount':1000,'cap':0,'zero_pool':True,'vault_amount':0,'migration_fee':fee}
 for cap in [1,1000000,10**12]:yield {'name':f'cap{cap}','fees':[95,30],'amount':10**9,'cap':cap}

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for c in cases():
  o=h.invoke(False,c['amount'],mutation=mutation(c));b=h.invoke(False,c['amount'],a.candidate,mutation(c));diff=[k for k in ['error','events','inner','return_data','before','after'] if o[k]!=b[k]];rows.append({'case':c,'original':o,'candidate':b,'different_fields':diff});print(c['name'],o['error'],b['error'],diff,flush=True)
 a.output.write_bytes(gzip.compress(json.dumps({'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]},separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
