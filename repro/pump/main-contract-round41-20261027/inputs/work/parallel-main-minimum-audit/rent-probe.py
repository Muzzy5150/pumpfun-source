import sys,json,gzip,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import pump_minimum_fee_differential as f
from solders.rent import Rent
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
rows=[]
for lpy in [7205759403792,7205759403793]:
 for bps in [1,2,10000]:
  c={'shares':[bps],'recipient_lamports':0,'amount':0};original=f.f.LiteSVM
  class RentVM(original):
   def set_account(self,address,account):
    if address==f.VAULT:
     self.set_rent(Rent(lpy,2.0,50));super().set_account(f.PAYER.pubkey(),f.Account(10**18,b'',f.Pubkey.default()))
    return super().set_account(address,account)
  f.f.LiteSVM=RentVM
  try:o=f.run(c);n=f.run(c,a.candidate)
  finally:f.f.LiteSVM=original
  diff=[k for k in ['error','events','before','after'] if o[k]!=n[k]]+[k for k in ['return_data','inner_instructions'] if o['metadata'][k]!=n['metadata'][k]]
  row={'case':{'rent_lamports_per_byte_year':lpy,**c},'original':o,'candidate':n,'different_fields':diff};rows.append(row)
  print(json.dumps({'case':row['case'],'original_error':o['error'],'candidate_error':n['error'],'events':o['events'],'different_fields':diff}),flush=True)
r={'cases':rows,'case_count':len(rows),'mismatches':[i for i,x in enumerate(rows) if x['different_fields']],'diagnostics':audit({'rent':rows})};a.output.write_bytes(gzip.compress(json.dumps(r).encode()))
