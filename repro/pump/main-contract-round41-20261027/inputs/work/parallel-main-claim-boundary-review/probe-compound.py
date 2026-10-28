"""Signed claim post-transfer overflow and zero-payout CPI precedence cases."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,re,sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'scripts'))
sys.path.insert(0,str(R/'work/parallel-main-incentives-next'))
import probe_claim_accounts_v2 as adapted
from solders.transaction import Transaction
from pump_diagnostic_audit import audit

def cases():
 for claimed in [0,2**64-1]:
  for amount in [0,1,200]:
   for fault in ['none','empty-source','frozen-source','frozen-destination']:
    c={'name':f'claim-claimed{claimed}-amount{amount}-{fault}','claimed':claimed,'has_claimed':int(claimed>0),'volume':0,'unclaimed':amount}
    if fault=='empty-source':c['vault_amount']=0
    if fault=='frozen-source':c['mutations']={'global_ata':{'patches':[[108,'02']]}}
    if fault=='frozen-destination':c['mutations']={'user_ata':{'patches':[[108,'02']]}}
    yield c
 for period in [-1,0,1]:
  for amount in [0,1]:
   yield {'name':f'before-start-period{period}-pending{amount}','now':9,'start':10,'end':39,'last':0,'seconds_in_a_day':period,'volume':0,'unclaimed':amount,'claimed':2**64-1,'has_claimed':1}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 rows=[]
 for c in cases():
  o=adapted.fixture.run_case(adapted.fixture.ORIGINAL,c);n=adapted.fixture.run_case(a.candidate,c)
  assert o['transaction_base64']==n['transaction_base64'];Transaction.from_bytes(base64.b64decode(o['transaction_base64'])).verify()
  fields=['error','error_code','success','before','after','user_after','event_data_base64','inner'];diff=[k for k in fields if o[k]!=n[k]]
  logs=lambda side:[l for l in side['logs']if re.match(r'^Program [1-9A-HJ-NP-Za-km-z]+ (?:invoke \[|success$|failed:)',l)]
  if logs(o)!=logs(n):diff.append('invocations')
  if adapted.diagnostics(o)!=adapted.diagnostics(n):diff.append('diagnostics')
  row={'case':c,'original':o,'candidate':n,'different_fields':diff};rows.append(row)
  print(json.dumps({'case':c['name'],'error':o['error'],'diff':diff}),flush=True)
 diag=audit({'claim-compound':rows});h=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
 result={'scope':__doc__,'candidate_sha256':h(a.candidate),'script_sha256':h(Path(__file__)),'adapter_sha256':h(Path(adapted.__file__)),'fixture_sha256':h(Path(adapted.fixture.__file__)),'case_count':len(rows),'cases':rows,'mismatches':[r['case']['name']for r in rows if r['different_fields']],'diagnostics':diag}
 a.output.write_bytes(gzip.compress(json.dumps(result).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':result['mismatches'],'diagnostic_mismatches':diag['mismatches']}));assert not result['mismatches'] and not diag['mismatches']
if __name__=='__main__':main()
