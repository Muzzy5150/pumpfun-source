from pathlib import Path
import json,gzip,hashlib,importlib.util,sys,argparse
import fence_route_fixture as h
R=Path(__file__).resolve().parents[2];W=R/'work/parallel-main-trading';ap=argparse.ArgumentParser();ap.add_argument('--candidate',type=Path,default=W/'build-corrected-01/candidate.so');ap.add_argument('--output',type=Path,default=W/'remaining-fences.json.gz');args=ap.parse_args();b=args.candidate;rows=[]
cases=[]
for role in ['source','destination','base_vault_0','base_vault_1','quote_vault_1','buyback']:
 for length in [166,178]:
  for typebyte in [0,2]:cases.append({'name':f'{role}_len{length}_type{typebyte}','account_mutations':{role:{'length':length,'bytes':[[165,typebyte]]}}})
for role in ['base_mint_0','base_mint_1']:
 for length in [83,166,200]:
  mutations={'length':length}
  if length>=166:mutations['bytes']=[[165,1]]
  cases.append({'name':f'{role}_len{length}','account_mutations':{role:mutations}})
for role in ['curve_0','curve_1']:
 for length in [83,115,141,165]:cases.append({'name':f'{role}_len{length}','account_mutations':{role:{'length':length}}})
 for reserve in [0,1,1000000]:cases.append({'name':f'{role}_completion_{reserve}','account_mutations':{role:{'u64':[[24,reserve]]}}})
for c in cases:
 o=h.invoke(False,10**9,'captured',case=c);v=h.invoke(False,10**9,'captured',candidate=b,case=c);diff=[k for k in ['error','events','inner','return_data','before','after','pump_calls','token_calls'] if o[k]!=v[k]]
 reached=any('Instruction: MultiHopCurveSwap' in s for s in o['logs']);rows.append({'case':c,'original':o,'candidate':v,'different_fields':diff,'original_reached_pump':reached});print(c['name'],o['error'],v['error'],reached,diff,flush=True)
# Existing captured-base Token2022 fixture through the immutable AMM.
path=R/'repro/pump/pr5-517-integration/harness/pump_multi_hop_curve_differential.py'
sys.path.insert(0,str(path.parent));spec=importlib.util.spec_from_file_location('token22_route_oracle',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
for sell in [False,True]:
 c={'name':f'base_token2022_{sell}','sell':sell,'amount':10**6,'limit':1};o=m.execute(c,R/'evidence/original/pump/deployed.so');v=m.execute(c,b);diff=[k for k in ['error','events','inner','return_data','before','after'] if o[k]!=v[k]];reached=any('Instruction: MultiHopCurveSwap' in s for s in o['logs']);rows.append({'case':c,'original':o,'candidate':v,'different_fields':diff,'original_reached_pump':reached});print(c['name'],o['error'],v['error'],reached,diff,flush=True)
report={'scope':'Offline synthetic mutations through immutable original AMM; original_reached_pump distinguishes upstream rejection from main contract coverage.','candidate_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]};args.output.write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
