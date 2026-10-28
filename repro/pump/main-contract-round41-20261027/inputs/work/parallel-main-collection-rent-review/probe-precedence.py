"""Independent creator-collection rent arithmetic and error-order controls."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,re,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_creator_collect_v2_differential as fixture
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction
FEES='pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ'

def cases():
 for version in ['legacy','v2']:
  for amount in [0,1]:
   for owner in [FEES,str(fixture.P),str(fixture.TOKEN)]:
    yield {'name':f'{version}-owner-{owner}-amount{amount}','version':version,'native':890880+amount,'patch':{'creator':{'owner':owner,'lamports':0,'bytes':[(0,'00'*8)]}}}
   yield {'name':f'{version}-executable-amount{amount}','version':version,'native':890880+amount,'executable':True}
   for fault in ['owner','data']:
    patch={'owner':str(fixture.TOKEN)}if fault=='owner'else{'bytes':[(0,'00')]}
    yield {'name':f'{version}-invalid-vault-{fault}-lowrecipient-amount{amount}','version':version,'native':890880+amount,'patch':{'creator':{'lamports':0},'creator_vault':patch}}
  for recipient,amount in [(2**64-2,1),(2**64-1,1),(2**64-2,3)]:
   yield {'name':f'{version}-overflow-recipient{recipient}-amount{amount}','version':version,'native':890880+amount,'patch':{'creator':{'lamports':recipient}}}
  for length in [1,165,1024]:
   floor=(128+length)*6960
   for delta in [-1,0]:
    yield {'name':f'{version}-datalen{length}-floor-delta{delta}','version':version,'native':890881,'patch':{'creator':{'lamports':floor-1+delta,'owner':str(fixture.P),'bytes':[(0,'00'*length)]}}}
 for amount in [0,1]:
  yield {'name':f'token-executable-invalid-source-amount{amount}','version':'v2','quote':str(fixture.QUOTE),'tokens':amount,'executable':True,'source_missing':True}
  yield {'name':f'token-fees-owner-invalid-source-amount{amount}','version':'v2','quote':str(fixture.QUOTE),'tokens':amount,'source_missing':True,'patch':{'creator':{'owner':FEES,'lamports':0}}}

def run(c,binary=None):
 old=fixture.IX
 try:
  fixture.IX=next(x for x in fixture.J['instructions']if x['name']==('collect_creator_fee'if c['version']=='legacy'else'collect_creator_fee_v2'))
  return fixture.run(c,binary)
 finally:fixture.IX=old

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();rows=[]
 for c in cases():
  o,n=run(c),run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64']
  for side in [o,n]:assert all(VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
  diff=[k for k in ['error','before','after','events','inner','returns']if o[k]!=n[k]]
  plain=lambda x:[l for l in x['logs']if l in ['Program log: No creator fee to collect','Program log: Creator account is executable, so it cannot receive lamports','Program log: Creator account does not have enough rent-exemption lamports']]
  if plain(o)!=plain(n):diff.append('plain_logs')
  seq=lambda x:[l for l in x['logs']if re.match(r'^Program [1-9A-HJ-NP-Za-km-z]+ (?:invoke \[|success$|failed:)',l)]
  if seq(o)!=seq(n):diff.append('invocations')
  rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
 diag=audit({'collection_precedence':rows});h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();d={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[r['case']['name']for r in rows if r['different_fields']],'diagnostics':diag,'candidate_sha256':h(a.candidate),'script_sha256':h(Path(__file__)),'fixture_sha256':h(Path(fixture.__file__))};a.output.write_bytes(gzip.compress(json.dumps(d).encode(),mtime=0));print({'cases':len(rows),'mismatches':len(d['mismatches']),'diagnostic_mismatches':len(diag['mismatches'])})
if __name__=='__main__':main()
