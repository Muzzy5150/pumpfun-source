"""Keep recipients live while checking owner and invalid-vault precedence."""
from pathlib import Path
import importlib.util
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('collection_precedence',P/'probe-precedence.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
def cases():
 for version in ['legacy','v2']:
  for amount in [0,1]:
   for recipient in [1,2000000]:
    for owner in [base.FEES,str(base.fixture.P),str(base.fixture.TOKEN)]:
     yield {'name':f'{version}-live{recipient}-owner{owner}-amount{amount}','version':version,'native':890880+amount,'patch':{'creator':{'owner':owner,'lamports':recipient,'bytes':[(0,'00'*8)]}}}
  for fault in ['owner','data']:
   patch={'owner':str(base.fixture.TOKEN)}if fault=='owner'else{'bytes':[(0,'00')]}
   yield {'name':f'{version}-funded-recipient-invalid-vault-{fault}','version':version,'native':890881,'patch':{'creator':{'lamports':2000000},'creator_vault':patch}}
 for amount in [0,1]:
  for missing in [False,True]:
   yield {'name':f'token-live-FEES-amount{amount}-missing{missing}','version':'v2','quote':str(base.fixture.QUOTE),'tokens':amount,'source_missing':missing,'patch':{'creator':{'owner':base.FEES,'lamports':1}}}
base.cases=cases
if __name__=='__main__':base.main()
