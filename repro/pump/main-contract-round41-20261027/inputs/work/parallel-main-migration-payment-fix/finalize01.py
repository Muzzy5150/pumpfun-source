from pathlib import Path
import base64,difflib,gzip,hashlib,json,re,struct,sys
from solders.transaction import VersionedTransaction
from solders.rent import Rent
from elftools.elf.elffile import ELFFile
P=Path(__file__).resolve().parent;R=P.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(R/'scripts'));from pump_diagnostic_audit import audit

def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def input_key(o):return hashlib.sha256((o['transaction_base64']+json.dumps({k:v for k,v in o['before'].items()if v is not None},sort_keys=True,separators=(',',':'))).encode()).hexdigest()
state={**read(P/'full-state01.json'),**read(P/'leaf-state01.json')};assert len(state)==8 and all(r['returncode']==0 for r in state.values());receipts={name:read(Path(row['output']))for name,row in state.items()};receipts['new']=read(P/'new01.json.gz');counts={};transactions=signatures=0;invocations={};existing=set()
for name,j in receipts.items():
 assert not j.get('mismatches');rows=j['cases'];counts[name]=len(rows);assert len(rows)==j['case_count'];bad=[]
 for i,row in enumerate(rows):
  assert not row.get('mismatches')and not row.get('different_fields')and not row.get('mismatched_fields'),(name,i)
  o,n=row['original'],row['candidate'];assert o['transaction_base64']==n['transaction_base64']
  for side in [o,n]:
   tx=VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64']));assert all(tx.verify_with_results());transactions+=1;signatures+=len(tx.signatures)
  seq=lambda side:[l for l in side['logs']if re.match(r'^Program [1-9A-HJ-NP-Za-km-z]+ (?:invoke \[|success$|failed:)',l)]
  if seq(o)!=seq(n):bad.append(i)
  if name!='new':existing.add(input_key(o))
 assert not bad;invocations[name]={'cases':len(rows),'mismatches':bad}
assert sum(counts.values())==1228 and counts['new']==36
newkeys=[input_key(r['original'])for r in receipts['new']['cases']];assert len(set(newkeys))==36 and not(set(newkeys)&existing)
diag=audit(receipts);assert not diag['mismatches'];(P/'diagnostics01.json').write_text(json.dumps(diag,indent=2)+'\n');(P/'invocations01.json').write_text(json.dumps(invocations,indent=2)+'\n')
SYS='11111111111111111111111111111111';amount_rows=[]
for row in receipts['new']['cases']:
 c=row['case'];o,n=row['original'],row['candidate']
 if c.get('funded_boost_lamports')is None or o['error']is not None:continue
 tx=VersionedTransaction.from_bytes(base64.b64decode(o['transaction_base64']));keys=tx.message.account_keys;user=o['names']['user'];pa=o['names']['pool_authority']
 def payments(side):
  result=[]
  for group in side['inner']:
   for entry in group:
    ins=entry['instruction'];data=bytes(ins['data'][1:]);a=ins['accounts'][1:]
    if str(keys[ins['programIdIndex']])==SYS and len(data)==12 and int.from_bytes(data[:4],'little')==2:
     fr,to=str(keys[a[0]]),str(keys[a[1]])
     if (fr,to)in[(user,pa),(pa,user)]:result.append(('forward'if fr==user else'refund',int.from_bytes(data[4:],'little')))
  return result
 op,np=payments(o),payments(n);assert op==np;minimum=Rent.default().minimum_balance(165)
 expected=[('forward',minimum)]
 if not c['name'].startswith('legacy'):
  if c.get('stable'):
   globaldata=bytes.fromhex(o['before'][o['names']['global']]['data']);expected.insert(0,('forward',int.from_bytes(globaldata[146:154],'little')))
  expected.append(('refund',minimum))
 assert op==expected,(c['name'],op,expected);amount_rows.append({'case':c['name'],'payments':op,'candidate_equal':True})
assert len(amount_rows)==6;(P/'amount-audit01.json').write_text(json.dumps({'cases':amount_rows,'rent_minimum_165':Rent.default().minimum_balance(165)},indent=2)+'\n')
inv=read(P/'inventory01.json');delta=read(P/'window-gains01.json');assert inv['counts']=={'total':1035,'raw':124,'normalized':733,'unmatched':302};assert all(not x['gains']and not x['losses']for x in delta['sets'].values())
comp=read(P/'native01.json');match=next(x for x in comp['candidates']if x['normalized_equal']);target=match['start'];callees=[]
for orig in comp['original_operands']:
 if orig['kind']!='direct-call':continue
 actual=next(x for x in match['operands']if x['offset']==orig['offset']);window=next(w for w in inv['windows']if w['start']==orig['target']);matches=[m for m in window['normalized_matches']if m['start']==actual['target']];assert matches;callees.append({'offset':orig['offset'],'original':hex(orig['target']),'candidate':hex(actual['target']),'bytes':window['bytes'],'symbols':[m['symbol']for m in matches]})
with(P/'build01/unstripped.so').open('rb')as f:
 e=ELFFile(f);t=e.get_section_by_name('.text');data=t.data();start=t['sh_addr'];syms=[(s['st_value'],s['st_size'],s.name)for s in e.get_section_by_name('.symtab').iter_symbols()if s['st_info']['type']=='STT_FUNC'and s['st_size']];calls=[];p=0
 while p<len(data):
  op,regs,_,imm=struct.unpack_from('<BBhi',data,p);pc=start+p
  if op==0x85 and regs>>4==1 and pc+8+imm*8==target:calls.append({'site':hex(pc),'owners':[name for a,n,name in syms if a<=pc<a+n]})
  p+=16 if op==0x18 else 8
assert len(calls)==4,calls;(P/'native-call-proof01.json').write_text(json.dumps({'original':'0x8e450','bytes':1208,'candidate':hex(target),'actual_candidate_calls':calls,'original_caller_proof':'work/parallel-main-migration-payment-alias/CALLER-PROOF.json','callees':callees},indent=2)+'\n')
source=P/'source01';baseline=R/'work/parallel-main-multihop-native-edge/source01';files=['src/migrate.rs','src/migrate_v2.rs','src/migration_native_payments.rs'];patch=[]
for name in files:
 a,b=baseline/name,source/name;patch.extend(difflib.unified_diff(a.read_text().splitlines(True)if a.exists()else[],b.read_text().splitlines(True),fromfile='a/'+name if a.exists()else'/dev/null',tofile='b/'+name))
(P/'migration-payment01.patch').write_text(''.join(patch));(P/'SOURCE-MANIFEST01.json').write_text(json.dumps({str(f.relative_to(source)):sha(f)for f in sorted(source.rglob('*'))if f.is_file()},indent=2)+'\n')
build=read(P/'build01/build-comparison.json');assert build['returncode']==0 and build['source_unchanged'];specs=read(R/'work/parallel-main-migration-payment-alias/DEDUPLICATED-SPECS.json')
result={'status':'validated isolated migration boost policy and funding correction','baseline':'frozen R32 draft plus accepted MultiHop edge','source_hashes':{name:sha(source/name)for name in files},'candidate_sha256':sha(P/'build01/candidate.so'),'unstripped_sha256':sha(P/'build01/unstripped.so'),'build_receipt_sha256':sha(P/'build01/build-comparison.json'),'patch_sha256':sha(P/'migration-payment01.patch'),'inventory':inv['counts'],'full_sets':delta['sets'],'native_transfer_body':{'original':'0x8e450','bytes':1208,'normalized_exact':True,'actual_candidate_call_count':len(calls)},'runtime':{'case_counts':counts,'total_cases':sum(counts.values()),'verified_transactions':transactions,'verified_signatures':signatures,'deduplicated_new_cases':36,'before_differing_new_cases':sum(bool(s['before_difference_fields'])for s in specs['specs']),'after_differing_new_cases':0,'diagnostic_mismatches':[],'invocation_sequence_mismatches':[],'amount_audit_cases':len(amount_rows)},'fixes':['0/1 remaining boost accounts are accepted when a valid old config or decoded boost_enabled=false permits skipping;2+provided accounts are still processed;mayhem skips.','Legacy fronts full token-account rent before boost CPI.','V2 fronts full selected token-account rent, then refunds excess or replenishes the initial pool-authority balance.'],'limits':['Full ELF equality remains false.','No new normalized/raw windows are claimed; actual native callee/callers are restored.','AMM implementation is unchanged.','Parent combined source/profile validation remains required.']};(P/'RESULT01.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['candidate_sha256','unstripped_sha256','patch_sha256','runtime']},indent=2))
