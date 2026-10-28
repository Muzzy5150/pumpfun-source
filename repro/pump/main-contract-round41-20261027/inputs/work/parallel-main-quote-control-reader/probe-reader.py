"""Signed QuoteControl raw-reader range, order and duplicate-entry probes."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,struct,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_create_control_differential as f
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction

def cases():
 base={'instruction':'create_v2','quote':True,'quote_whitelisted':False,'quote_control':True}
 target=str(f.OTHER.pubkey());low=str(f.Pubkey.default());high=str(f.Pubkey.from_bytes(bytes([250])*32))
 variants=[[(target,77),(low,2),(high,3)],[(high,3),(target,77),(low,2)],[(low,2),(high,3),(target,77)],[(target,0),(target,999)],[(target,999),(target,0)],[(high,3),(target,1),(target,2),(low,4)],[(low,2),(high,3)]]
 for token22 in [False,True]:
  for index,entries in enumerate(variants):yield dict(base,case=f'order-{token22}-{index}',quote_token22=token22,control_entries=entries)
 entries=[(high,3),(low,2),(target,77)]
 for count in [0,1,2,3,4,2**32-1]:yield dict(base,case=f'declared-{count}',control_entries=entries,mutations={'quote_control':{'patches':[(104,struct.pack('<I',count).hex())]}})
 for length in [0,7,8,103,104,107,108,109,147,148,149,187,188,189]:yield dict(base,case=f'range-{length}',control_entries=entries,mutations={'quote_control':{'length':length}})
 for length in [107,108,228]:yield dict(base,case=f'wrong-disc-length-{length}',control_entries=entries,mutations={'quote_control':{'length':length,'patches':[(0,'ff')]}})

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();rows=[]
 for c in cases():
  o,n=f.run(c),f.run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64']
  for side in [o,n]:assert all(VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
  diff=[k for k in ['before','after','error','events','inner','return']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['case'],o['error'],n['error'],diff,flush=True)
 diag=audit({'quote-reader':rows});h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();d={'scope':__doc__,'candidate_sha256':h(a.candidate),'original_sha256':h(f.ORIGINAL),'script_sha256':h(Path(__file__)),'fixture_sha256':h(Path(f.__file__)),'case_count':len(rows),'cases':rows,'mismatches':[r['case']['case']for r in rows if r['different_fields']],'diagnostics':diag};a.output.write_bytes(gzip.compress(json.dumps(d).encode(),mtime=0));print({'cases':len(rows),'mismatches':len(d['mismatches']),'diagnostic_mismatches':len(diag['mismatches'])})
if __name__=='__main__':main()
