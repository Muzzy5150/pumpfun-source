"""Bounded nondefault Rent sysvar controls for zero extension funding."""
from pathlib import Path
import argparse,base64,gzip,hashlib,inspect,json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_extend_differential as f
from solders.rent import Rent
from solders.transaction import VersionedTransaction
from pump_diagnostic_audit import audit
text=inspect.getsource(f.run);needle='vm.set_clock(Clock(100,1700000000,0,0,1700000000));';assert text.count(needle)==1
text=text.replace(needle,needle+'vm.set_rent(Rent(c.get("rent_lamports_per_byte",3480),c.get("rent_threshold",2.0),50));')
ns=dict(f.__dict__);ns['Rent']=Rent;exec(compile(text,str(Path(__file__)), 'exec'),ns);run=ns['run']
def cases():
 for kind in ['BondingCurve','Global','GlobalVolumeAccumulator','UserVolumeAccumulator']:
  for mode in ['zero-lamports','zero-threshold']:
   yield {'name':kind+'-'+mode,'kind':kind,'size':8,'rent_lamports_per_byte':0 if mode=='zero-lamports' else 3480,'rent_threshold':0.0 if mode=='zero-threshold' else 2.0}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for c in cases():
  o,n=run(c),run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64']
  for side in [o,n]:assert all(VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
  diff=[k for k in ['before','after','error','events','inner','return']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
 d={'scope':__doc__,'case_count':len(rows),'cases':rows,'mismatches':[r['case']['name']for r in rows if r['different_fields']],'diagnostics':audit({'zero-rent':rows}),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'transformed_fixture_sha256':hashlib.sha256(text.encode()).hexdigest()};a.output.write_bytes(gzip.compress(json.dumps(d).encode(),mtime=0));print({'cases':len(rows),'mismatches':len(d['mismatches'])})
if __name__=='__main__':main()
