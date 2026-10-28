"""Signed claim zero-payout log regression with successful positive controls."""
from pathlib import Path
import gzip,hashlib,json,sys
import probe_claim_accounts_v2 as probe
old_diagnostics=probe.diagnostics
probe.diagnostics=lambda r:old_diagnostics(r)+[l for l in r['logs'] if l=='Program log: No tokens to claim']
def cases():
 yield {'name':'claim-positive-control'}
 yield {'name':'claim-pending-positive-control','volume':0,'unclaimed':1}
 yield {'name':'claim-zero-volume-log','volume':0,'unclaimed':0}
 yield {'name':'claim-zero-supply-log','supply':0,'unclaimed':0}
if __name__=='__main__':
 probe.cases=cases
 try:probe.main()
 finally:
  if '--output' in sys.argv:
   p=Path(sys.argv[sys.argv.index('--output')+1])
   if p.exists():
    r=json.loads(gzip.decompress(p.read_bytes()));r['additional_scope']=__doc__;r['additional_probe_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0))
