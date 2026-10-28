from pathlib import Path
import base64,difflib,gzip,hashlib,json,re,sys
from solders.transaction import Transaction
P=Path(__file__).resolve().parent;R=P.parents[1]
sys.path.insert(0,str(R/'scripts'));from pump_diagnostic_audit import audit
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def rows(j):return j.get('cases')or [r for group in j.get('suites',{}).values()for r in group]
state=read(P/'runtime-state01.json');assert len(state)==22 and all(r['returncode']==0 for r in state.values());receipts={k:read(Path(v['output']))for k,v in state.items()};counts={};invokes={}
for name,j in receipts.items():
 rs=rows(j);assert len(rs)==j['case_count'];assert not j.get('mismatches');counts[name]=len(rs);bad=[]
 for i,row in enumerate(rs):
  assert not row.get('different_fields')and not row.get('mismatches')and row.get('match',True),(name,i)
  o,n=row['original'],row['candidate'];verified=lambda x:x.get('signature_verified',x.get('signatures_verified',x.get('verified_signature_count',0)>0));assert verified(o)and verified(n),(name,i,'signature');assert o['transaction_base64']==n['transaction_base64']
  selected=lambda x:[s for s in x.get('logs',[])if re.match(r'^Program [1-9A-HJ-NP-Za-km-z]+ (?:invoke \[|success$|failed:)',s)]
  if selected(o)!=selected(n):bad.append(i)
 assert not bad,(name,bad);invokes[name]={'cases':len(rs),'mismatches':bad}
assert sum(counts.values())==1275
diag=audit(receipts);assert not diag['mismatches'];(P/'diagnostics01.json').write_text(json.dumps(diag,indent=2)+'\n');(P/'invocations01.json').write_text(json.dumps(invokes,indent=2)+'\n')
# Decode the explicit48 cases independently to prove the zero-fee creator CPI gate.
idl=read(R/'evidence/upstream/pump.json');byname={x['name']:x for x in idl['instructions']};SYS='11111111111111111111111111111111';TOKENS={'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA','TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'}
control=[]
for row in rows(receipts['owned-order48']):
 case=row['case'];tx=Transaction.from_bytes(base64.b64decode(row['original']['transaction_base64']));keys=tx.message.account_keys;ix=tx.message.instructions[-1];named={f['name']:keys[i]for f,i in zip(byname[case['kind']]['accounts'],ix.accounts)}
 cashback='_cashback_True_'in case['name'];zero='_zero_creator_True_'in case['name'];token=case['token_quote'];target=named[('associated_user_volume_accumulator'if cashback else'associated_creator_vault')if token else('user_volume_accumulator'if cashback else'creator_vault')]
 def payments(side):
  out=[]
  for group in side['inner']:
   for entry in group:
    ins=entry['instruction'];program=str(keys[ins['programIdIndex']]);aa=ins['accounts'][1:];data=bytes(ins['data'][1:])
    if program==SYS and len(data)==12 and int.from_bytes(data[:4],'little')==2:
     dest=keys[aa[1]];amount=int.from_bytes(data[4:],'little')
    elif program in TOKENS and len(data)==10 and data[0]==12:
     dest=keys[aa[2]];amount=int.from_bytes(data[1:9],'little')
    else:continue
    if dest==target:out.append(amount)
  return out
 op,np=payments(row['original']),payments(row['candidate']);assert op==np;assert len(op)==(0 if zero else 1),(case['name'],op)
 control.append({'case':case['name'],'zero_creator':zero,'cashback':cashback,'creator_payments':op,'same_candidate_payments':True,'original_error':row['original']['error']})
(P/'owned-order-audit01.json').write_text(json.dumps({'cases':48,'zero_fee_cases':sum(r['zero_creator']for r in control),'nonzero_fee_cases':sum(not r['zero_creator']for r in control),'all_zero_fee_creator_payments_absent':True,'all_positive_fee_creator_payments_present':True,'rows':control},indent=2)+'\n')
# Independently decode the recipient sequence, including zero shares and failures.
recipient_control=[]
for row in rows(receipts['payment-order64']):
 case=row['case'];tx=Transaction.from_bytes(base64.b64decode(row['original']['transaction_base64']));keys=tx.message.account_keys;ix=tx.message.instructions[-1];named={f['name']:keys[i]for f,i in zip(byname[case['kind']]['accounts'],ix.accounts)}
 token=case['token_quote'];targets={named['associated_quote_fee_recipient'if token else'fee_recipient']:'protocol',named['associated_quote_buyback_fee_recipient'if token else'buyback_fee_recipient']:'buyback'}
 def recipient_payments(side):
  found=[]
  for group in side['inner']:
   for entry in group:
    ins=entry['instruction'];program=str(keys[ins['programIdIndex']]);aa=ins['accounts'][1:];data=bytes(ins['data'][1:])
    if program==SYS and len(data)==12 and int.from_bytes(data[:4],'little')==2:dest=keys[aa[1]];amount=int.from_bytes(data[4:],'little')
    elif program in TOKENS and len(data)==10 and data[0]==12:dest=keys[aa[2]];amount=int.from_bytes(data[1:9],'little')
    else:continue
    if dest in targets:found.append((targets[dest],amount))
  return found
 op,np=recipient_payments(row['original']),recipient_payments(row['candidate']);assert op==np
 assert all(amount>0 for _,amount in op);labels=[name for name,_ in op];assert labels in [[],['protocol'],['buyback'],['protocol','buyback']],(case['name'],op)
 global_patch=case['account_mutations']['global'];waived=bool(global_patch.get('bytes'));bps=global_patch['u64'][0][1]
 if waived:assert not op,(case['name'],op)
 if not waived and bps==0:assert labels==['protocol'],(case['name'],op)
 if not waived and bps==10000:assert labels==['buyback'],(case['name'],op)
 recipient_control.append({'case':case['name'],'waived':waived,'basis_points':bps,'payments':op,'same_candidate_payments':True,'error':row['original']['error']})
(P/'recipient-order-audit01.json').write_text(json.dumps({'cases':len(recipient_control),'no_zero_amount_recipient_cpis':True,'protocol_before_buyback':True,'all_waived_recipient_cpis_absent':True,'rows':recipient_control},indent=2)+'\n')
inv=read(P/'inventory01.json');base=read(R/'work/parallel-main-user-quote-generic/inventory02.json');assert inv['counts']=={'total':1035,'raw':124,'normalized':733,'unmatched':302};sets=read(P/'window-gains01.json');assert sets['sets']=={'normalized_matches':{'gains':['0x8d108'],'losses':[]},'raw_match':{'gains':[],'losses':[]}}
by={r['start']:r for r in inv['windows']};proof=[]
for name in ['wrapper01.json','native01.json','borrowed-wrapper01.json','borrowed-native01.json','owned-wrapper01.json','owned-native01.json']:
 j=read(P/name);c=next(x for x in j['candidates']if x['normalized_equal']);cs={x['offset']:x for x in c['operands']}
 for x in j['original_operands']:
  if x['kind']!='direct-call':continue
  y=cs[x['offset']];matches=[m for m in by[x['target']]['normalized_matches']if m['start']==y['target']];assert matches
  proof.append({'source_original':hex(j['original_start']),'source_candidate':hex(c['start']),'offset':x['offset'],'original_target':hex(x['target']),'candidate_target':hex(y['target']),'bytes':by[x['target']]['bytes'],'matching_symbols':[m['symbol']for m in matches]})
(P/'callees01.json').write_text(json.dumps(proof,indent=2)+'\n')
source=P/'source01';baseline=R/'work/parallel-main-user-quote-generic/source02';files=['src/lib.rs','src/buy_v2.rs'];patch=[]
for f in files:patch.extend(difflib.unified_diff((baseline/f).read_text().splitlines(True),(source/f).read_text().splitlines(True),fromfile='a/'+f,tofile='b/'+f))
(P/'recipient-quote01.patch').write_text(''.join(patch));(P/'SOURCE-MANIFEST01.json').write_text(json.dumps({str(p.relative_to(source)):sha(p)for p in sorted(source.rglob('*'))if p.is_file()},indent=2)+'\n')
build=read(P/'build01/build-comparison.json');assert build['returncode']==0 and build['source_unchanged']
result={'status':'validated nested borrowed recipient quote-payment increment for parent composition','base':'sealed owned-payment/source02','candidate_sha256':sha(P/'build01/candidate.so'),'unstripped_sha256':sha(P/'build01/unstripped.so'),'build_receipt_sha256':sha(P/'build01/build-comparison.json'),'source_hashes':{f:sha(source/f)for f in files},'patch_sha256':sha(P/'recipient-quote01.patch'),'inventory':inv['counts'],'window_sets':sets['sets'],'new_actual_exact_bodies':{'0x97bf0':704,'0x8d108':1216},'newly_matching_window':'0x8d108','preserved_actual_exact_bodies':{'0x97930':704,'0x8df98':1208,'0x97eb0':864,'0x8da98':1280},'callees':proof,'runtime':{'case_count':1275,'suite_counts':counts,'all_signatures_verified':True,'transaction_bytes_identical':True,'strict_fixture_mismatches':[],'diagnostic_mismatches':[],'invocation_sequence_mismatches':[],'explicit_owned_zero_and_failure_cases':48,'zero_fee_creator_cpi_absence_proved_cases':24,'positive_fee_creator_cpi_presence_proved_cases':24,'recipient_order_cases':64,'no_zero_recipient_cpis':True,'protocol_before_buyback':True},'limits':['Full original ELF identity remains false.','Common original Location objects prove shared source spans but not the exact original generic implementation; earlier generic control remains negative and frozen in parallel-main-user-quote-generic.','New concrete API preserves typed Signer and nested borrowed UncheckedAccount; exact original source names are unknown.','The former97bf0 duplicate match now has its own matching native callee; the8e450 alias retains its earlier caveat.','Other legacy direct callers of0x8da98 and MultiHop direct caller of0x8df98 remain unrefactored.','Root composite must complete its own full validation.']}
(P/'RESULT01.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'candidate':result['candidate_sha256'],'unstripped':result['unstripped_sha256'],'source':result['source_hashes'],'patch_sha256':result['patch_sha256'],'cases':1275},indent=2))
