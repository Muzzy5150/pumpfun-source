"""Signed claim multi-fault precedence probes for the typed self-program gate."""
from pathlib import Path
import gzip,hashlib,json,sys
import probe_claim_accounts_v2 as probe

old_alter=probe.alter_metas
def alter_metas(metas,case):
 metas=old_alter(metas,case)
 for role in case.get('unsigned',[]):
  i=probe.ROLE_NAMES.index(role);m=metas[i];metas[i]=probe.AccountMeta(m.pubkey,False,m.is_writable)
 return metas
probe.fixture.alter_metas=alter_metas

def cases():
 for zero in [False,True]:
  base={'volume':0,'unclaimed':0} if zero else {}
  yield dict(base,name=f'valid-program-zero-{zero}')
  yield dict(base,name=f'unsigned-payer-only-zero-{zero}',unsigned=['payer'],separate_fee_payer=True)
  yield dict(base,name=f'wrong-program-unsigned-payer-zero-{zero}',wrong_program_account=True,unsigned=['payer'],separate_fee_payer=True)
  yield dict(base,name=f'wrong-program-readonly-payer-zero-{zero}',wrong_program_account=True,readonly=['payer'],separate_fee_payer=True)
  yield dict(base,name=f'wrong-program-readonly-user-volume-zero-{zero}',wrong_program_account=True,readonly=['user_volume'])
  yield dict(base,name=f'wrong-program-wrong-event-zero-{zero}',wrong_program_account=True,wrong_event_authority=True)
  yield dict(base,name=f'wrong-program-wrong-global-seeds-zero-{zero}',wrong_program_account=True,wrong_global_pda=True)
  yield dict(base,name=f'wrong-program-wrong-user-seeds-zero-{zero}',wrong_program_account=True,wrong_user_pda=True)
  yield dict(base,name=f'wrong-program-wrong-ata-authority-zero-{zero}',wrong_program_account=True,mutations={'user_ata':{'patches':[(32,'fe'*32)]}})
  yield dict(base,name=f'wrong-program-wrong-global-mint-zero-{zero}',wrong_program_account=True,mutations={'global_volume':{'patches':[(32,'fe'*32)]}})

if __name__=='__main__':
 probe.cases=cases
 try:probe.main()
 finally:
  if '--output' in sys.argv:
   path=Path(sys.argv[sys.argv.index('--output')+1])
   if path.exists():
    record=json.loads(gzip.decompress(path.read_bytes()));record['additional_scope']=__doc__
    record['additional_probe_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    path.write_bytes(gzip.compress(json.dumps(record).encode(),mtime=0))
