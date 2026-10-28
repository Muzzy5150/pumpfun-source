"""Reach token-planner executable-recipient logging with genuine loaded program accounts."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
import pump_creator_distribution_differential as fixture
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction

def cases():
 q=fixture.Pubkey.from_bytes(bytes([88])*32)
 for token22 in [False,True]:
  for label,key in [('pump',fixture.PUMP),('token',fixture.TOKEN)]:
   for amount in [0,1000000]:
    yield {'name':f'token22={token22}/recipient={label}/amount={amount}','op':'distribute_creator_fees_v2','quote':str(q),'curve_patches':[(83,bytes(q).hex())],'remaining_atas':True,'grouped_remaining':True,'old_shareholders':[(str(key),10000)],'remaining':[(str(key),False)],'token22':token22,'pump_tokens':amount}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for c in cases():
  o=fixture.run(c);n=fixture.run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64']
  expected='Program log: Unable to distribute to '+c['old_shareholders'][0][0]+'. Shareholder is a program account, use pump_fees::update_fee_shares to remove the shareholder from the team'
  for side in[o,n]:
   assert expected in side['logs'],(c['name'],side['logs']);assert '6052'in str(side['error']);assert all(VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
  differences=[k for k in['error','before','after','events','inner','return']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':differences});print(c['name'],differences,flush=True)
 report={'scope':__doc__,'case_count':len(rows),'cases':rows,'branch_reached':len(rows),'mismatches':[r['case']['name']for r in rows if r['different_fields']],'diagnostics':audit({'token_executable':rows}),'inputs':{str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in[Path(__file__),Path(fixture.__file__),a.candidate,fixture.ORIGINAL]}}
 a.output.write_bytes(gzip.compress(json.dumps(report).encode(),mtime=0));assert not report['mismatches']and not report['diagnostics']['mismatches'];print('passed',len(rows))
if __name__=='__main__':main()
