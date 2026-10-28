"""Signed valid-baseline claim probes for the stored GlobalVolumeAccumulator mint gate."""
from pathlib import Path
import gzip,hashlib,json,sys
import probe_claim_accounts_v2 as probe

def cases():
 for zero in [False,True]:
  base={'volume':0,'unclaimed':0} if zero else {}
  yield dict(base,name=f'valid-stored-mint-zero-{zero}')
  yield dict(base,name=f'wrong-stored-mint-all-bytes-zero-{zero}',mutations={'global_volume':{'patches':[(32,'fe'*32)]}})
  yield dict(base,name=f'wrong-stored-mint-last-byte-zero-{zero}',mutations={'global_volume':{'patches':[(63,'fe')]}})

if __name__=='__main__':
 probe.cases=cases
 try:probe.main()
 finally:
  if '--output' in sys.argv:
   p=Path(sys.argv[sys.argv.index('--output')+1])
   if p.exists():
    r=json.loads(gzip.decompress(p.read_bytes()));r['additional_scope']=__doc__;r['additional_probe_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0))
