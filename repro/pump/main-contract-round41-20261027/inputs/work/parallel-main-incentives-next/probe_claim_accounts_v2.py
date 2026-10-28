"""Signed claim account-boundary probes with complete diagnostics and snapshots.

Reuses the retained captured claim fixture and changes only explicitly listed
account metadata, token ownership/program pairing, privileges, or remaining
accounts. Run through pump_with_captured_loader.py. No transaction is broadcast.
"""
from pathlib import Path
import argparse,base64,gzip,hashlib,inspect,itertools,json,re,sys

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
import pump_claim_token_incentives_differential as fixture
from solders.account import Account
from solders.instruction import AccountMeta
from solders.pubkey import Pubkey

TOKEN_LEGACY=Pubkey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
ROLE_NAMES=['user','user_ata','global_volume','global_ata','user_volume','mint','token_program','system_program','associated_token_program','event_authority','program','payer']
EXTRA_WATCH={}

def configured(vm,ordered,keys,global_ata,case):
 global EXTRA_WATCH
 EXTRA_WATCH={}
 vm.add_program_from_file(TOKEN_LEGACY,str(ROOT/'evidence/dependencies/spl_token/deployed.so'))
 if case.get('token_program')=='legacy':ordered[6]=TOKEN_LEGACY
 if case.get('rederive_atas'):
  for i,authority in [(1,ordered[0]),(3,ordered[2])]:
   new=Pubkey.find_program_address([bytes(authority),bytes(ordered[6]),bytes(ordered[5])],fixture.ATA)[0]
   account=vm.get_account(ordered[i]);vm.set_account(new,account);ordered[i]=new
  keys['user_base']=ordered[1];global_ata=ordered[3]
 for role,change in case.get('mutations',{}).items():
  key=ordered[ROLE_NAMES.index(role)];old=vm.get_account(key)
  if old is None:old=Account(0,b'',Pubkey.default())
  data=bytearray(old.data)
  for offset,value in change.get('patches',[]):
   raw=bytes.fromhex(value);data[offset:offset+len(raw)]=raw
  if 'length' in change:data=(data+bytes(max(0,change['length']-len(data))))[:change['length']]
  owner=change.get('owner',str(old.owner))
  owner={'legacy':str(TOKEN_LEGACY),'token22':str(fixture.TOKEN),'system':str(Pubkey.default()),'pump':str(fixture.PROGRAM),'other':str(fixture.OTHER.pubkey())}.get(owner,owner)
  vm.set_account(key,Account(change.get('lamports',old.lamports),bytes(data),Pubkey.from_string(owner),change.get('executable',old.executable),change.get('rent_epoch',old.rent_epoch)))
 for i,row in enumerate(case.get('remaining',[])):
  if 'role' in row:key=ordered[ROLE_NAMES.index(row['role'])]
  else:
   key=Pubkey.from_bytes(bytes([80+i])*32)
   vm.set_account(key,Account(row.get('lamports',1_000_000),bytes.fromhex(row.get('data','')),fixture.OTHER.pubkey(),row.get('executable',False),row.get('rent_epoch',0)))
  EXTRA_WATCH[f'remaining_{i}']=key
 EXTRA_WATCH.update({f'role_{role}':ordered[ROLE_NAMES.index(role)] for role in case.get('mutations',{}) if role!='program'})
 return ordered,global_ata

def alter_metas(metas,case):
 for role in case.get('readonly',[]):
  i=ROLE_NAMES.index(role);m=metas[i];metas[i]=AccountMeta(m.pubkey,m.is_signer,False)
 for i,row in enumerate(case.get('remaining',[])):
  metas.append(AccountMeta(EXTRA_WATCH[f'remaining_{i}'],False,row.get('writable',False)))
 return metas[:case.get('account_count',len(metas))]

def safe_snapshot(record):
 if record is None:return ['missing']
 data=base64.b64decode(record['data_base64'])
 if len(data)<114:return ['short',len(data)]
 return fixture.parse_user(data)

fixture.configured=configured;fixture.alter_metas=alter_metas;fixture.safe_snapshot=safe_snapshot
fixture.EXTRA_WATCH=EXTRA_WATCH
source=inspect.getsource(fixture.run_case)
needle='    idl = json.loads(IDL.read_text())'
assert source.count(needle)==1
source=source.replace(needle,'    ordered, global_ata = configured(vm, ordered, keys, global_ata, case)\n'+needle)
needle='    instruction = Instruction(PROGRAM, DISCRIMINATOR, metas)'
source=source.replace(needle,'    metas = alter_metas(metas, case)\n'+needle)
source=source.replace('    before = {name: account_record(vm, key) for name, key in watched.items()}','    watched.update(configured.__globals__["EXTRA_WATCH"])\n    before = {name: account_record(vm, key) for name, key in watched.items()}')
source=source.replace('''    tx = Transaction.new_signed_with_payer([instruction], PAYER.pubkey(),
                                            [PAYER], vm.latest_blockhash())''','''    fee_payer = OTHER if case.get('separate_fee_payer') else PAYER
    signer_keys = {m.pubkey for m in metas if m.is_signer} | {fee_payer.pubkey()}
    signers = [kp for kp in [PAYER, OTHER] if kp.pubkey() in signer_keys]
    tx = Transaction.new_signed_with_payer([instruction], fee_payer.pubkey(),
                                            signers, vm.latest_blockhash())''')
for side in ['before','after']:
 source=source.replace(f'parse_user(base64.b64decode({side}["user_volume"]["data_base64"]))',f'safe_snapshot({side}["user_volume"])')
exec(compile(source,str(Path(__file__)),'exec'),fixture.__dict__)

def cases():
 for zero in [False,True]:
  base={'volume':0,'unclaimed':0} if zero else {}
  yield dict(name=f'base-zero-{zero}',**base)
  for role in ['user','event_authority','payer','user_ata','global_volume','global_ata','user_volume','mint']:
   for mutation in [{'lamports':1},{'lamports':0},{'rent_epoch':2**64-1},{'executable':True},{'owner':'pump'},{'owner':'other'},{'length':0}]:
    yield dict(base,name=f'{role}-{mutation}-zero-{zero}',mutations={role:mutation},separate_fee_payer=True)
  for role in ['user_ata','global_volume','global_ata','user_volume','mint','payer']:
   yield dict(base,name=f'readonly-{role}-zero-{zero}',readonly=[role],separate_fee_payer=True)
  for role in ['user_ata','global_volume','global_ata','user_volume','mint']:
   for lamports in [1000,1_000_000]:yield dict(base,name=f'rent-{role}-{lamports}-zero-{zero}',mutations={role:{'lamports':lamports}})
  for count in [1,2,5]:yield dict(base,name=f'remaining-{count}-zero-{zero}',remaining=[{'data':'ff'} for _ in range(count)])
  for role in ['user','global_volume','user_volume','event_authority','payer']:
   yield dict(base,name=f'duplicate-extra-{role}-zero-{zero}',remaining=[{'role':role,'writable':True}])
  for program in ['legacy','token22']:
   for owners in itertools.product(['legacy','token22'],repeat=3):
    changes={role:{'owner':owner} for role,owner in zip(['mint','user_ata','global_ata'],owners)}
    if program=='legacy':changes['mint']['length']=82;changes['user_ata']['length']=165;changes['global_ata']['length']=165
    yield dict(base,name=f'token-cross-{program}-{owners}-zero-{zero}',token_program=program,rederive_atas=True,mutations=changes)

def diagnostics(result):
 return [re.sub(r' thrown in .*?:\d+\.', '.',line) for line in result['logs'] if any(s in line for s in ['AnchorError','Left:','Right:'])] + [line.split('\n',1)[-1] for line in result['logs'] if line.startswith('Program log: panicked at ')]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for c in cases():
  attempts=[]
  for binary in [fixture.ORIGINAL,a.candidate]:
   try:attempts.append(fixture.run_case(binary,c))
   except Exception as error:attempts.append({'fixture_rejected':type(error).__name__+': '+str(error)})
  x,y=attempts
  if 'fixture_rejected' in x or 'fixture_rejected' in y:
   rows.append(dict(case=c,original=x,candidate=y,differences=[],fixture_rejected=True))
   print(json.dumps({'fixture_rejected':c['name'],'original':x.get('fixture_rejected'),'candidate':y.get('fixture_rejected')}),flush=True)
   continue
  fields=['error','error_code','success','transaction_base64','before','after','user_after','event_data_base64','inner']
  diff=[k for k in fields if x[k]!=y[k]]
  if diagnostics(x)!=diagnostics(y):diff.append('diagnostics')
  rows.append(dict(case=c,original=x,candidate=y,differences=diff))
  if diff:print(json.dumps({'name':c['name'],'differences':diff,'original_error':x['error'],'candidate_error':y['error'],'original_diagnostics':diagnostics(x),'candidate_diagnostics':diagnostics(y)}),flush=True)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 record=dict(scope=__doc__,original_sha256=sha(fixture.ORIGINAL),candidate_sha256=sha(a.candidate),fixture_sha256=sha(Path(fixture.__file__)),adapter_sha256=sha(Path(__file__)),case_count=len(rows),executable_cases=sum(not r.get('fixture_rejected',False) for r in rows),fixture_rejections=[r['case']['name'] for r in rows if r.get('fixture_rejected')],mismatches=[r['case']['name'] for r in rows if r['differences']],cases=rows)
 a.output.write_bytes(gzip.compress(json.dumps(record).encode(),mtime=0))
 print(json.dumps({'cases':len(rows),'mismatches':record['mismatches']}));assert not record['mismatches']

if __name__=='__main__':main()
