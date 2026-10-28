"""Signed raw-account extension error operands and already-sized log controls."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,re,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_extend_differential as f
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction

def cases():
 for kind,size in [('BondingCurve',166),('Global',1088),('GlobalVolumeAccumulator',600),('UserVolumeAccumulator',137)]:
  for length in [0,7,8,size-1,size,size+1]:yield {'name':f'{kind}-length{length}','kind':kind,'size':length}
 for length in [0,7,8,166]:yield {'name':f'unknown-length{length}','kind':'unknown','size':length}
 for fields in [{'owner':str(f.TOKEN)},{'wrong':'system_program'},{'readonly':'account'},{'unsigned':'user'}]:yield {'name':'short-compound-'+str(fields),'size':7,**fields}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();rows=[]
 for c in cases():
  o,n=f.run(c),f.run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64']
  for side in [o,n]:assert all(VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
  diff=[k for k in ['before','after','error','events','inner','return']if o[k]!=n[k]]
  plain=lambda x:[l for l in x['logs']if l.startswith('Program log:')and not(l.startswith('Program log: Instruction:')or'AnchorError'in l or l.startswith(('Program log: Left:','Program log: Right:')))]
  if plain(o)!=plain(n):diff.append('plain_logs')
  rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],diff,plain(o),flush=True)
 d={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[r['case']['name']for r in rows if r['different_fields']],'diagnostics':audit({'extend-logs':rows})};a.output.write_bytes(gzip.compress(json.dumps(d).encode(),mtime=0));print({'cases':len(rows),'mismatches':len(d['mismatches']),'diagnostic_mismatches':len(d['diagnostics']['mismatches'])})
if __name__=='__main__':main()
