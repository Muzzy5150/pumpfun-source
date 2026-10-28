"""Read-only verification of paired Pump transaction retention and attribution.

Imports only decoding/cryptographic libraries. Never builds, signs, submits,
or executes a transaction. Logical substitutions add proven receipt fields;
input report objects and input files are not modified.
"""
from pathlib import Path
import base64,collections,gzip,hashlib,json,re
from solders.transaction import VersionedTransaction

ADDED_FIELDS=frozenset(['transaction_base64','transaction_sha256','signature_verification','instruction_attribution'])
EVENT_TAG='e445a52e51cb9a1d'
IDL_TAG='40f4bc78a7e9690a'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
 raw=Path(path).read_bytes();return json.loads(gzip.decompress(raw)if raw[:2]==b'\x1f\x8b'else raw)
def iter_pairs(value,path=''):
 if isinstance(value,dict):
  if isinstance(value.get('original'),dict)and isinstance(value.get('candidate'),dict):yield path,value
  for key,item in value.items():
   if key not in ('original','candidate'):yield from iter_pairs(item,path+'/'+key)
 elif isinstance(value,list):
  for i,item in enumerate(value):yield from iter_pairs(item,path+'/'+str(i))
def _decode_data(data):
 if isinstance(data,list):
  if data and isinstance(data[0],list):
   n=sum((x&127)<<(7*i)for i,x in enumerate(data[0]));raw=bytes(data[1:]);assert len(raw)==n,'Invalid short-vector length';return raw
  return bytes(data)
 if isinstance(data,str):
  alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';value=0
  for c in data:value=value*58+alphabet.index(c)
  return b'\0'*(len(data)-len(data.lstrip('1')))+(value.to_bytes((value.bit_length()+7)//8,'big')if value else b'')
 raise ValueError('Unsupported instruction-data representation')
def _inner_objects(value,path='inner'):
 if isinstance(value,dict):
  if ('programIdIndex'in value or'program_id_index'in value or'programId'in value)and'data'in value:yield path,value
  else:
   for key,item in value.items():yield from _inner_objects(item,path+'/'+key)
 elif isinstance(value,list):
  for i,item in enumerate(value):yield from _inner_objects(item,path+'/'+str(i))
def _main_logs(lines,program,log_names):
 stack=[];families=set();invocations=0
 for line in lines:
  m=re.match(r'^Program (\S+) invoke \[(\d+)\]$',line)
  if m:
   stack=stack[:int(m.group(2))-1]+[m.group(1)];invocations+=m.group(1)==program;continue
  m=re.match(r'^Program (\S+) (success|failed:.*)$',line)
  if m:
   for i in range(len(stack)-1,-1,-1):
    if stack[i]==m.group(1):stack=stack[:i];break
   continue
  m=re.match(r'^Program log: Instruction: (.+)$',line)
  if m and stack and stack[-1]==program:
   name=log_names.get(re.sub('[^a-z0-9]','',m.group(1).lower()))
   if name:families.add(name)
 return families,invocations

def verify_reports(full_path,additional_path,idl_path,*,root,candidate_sha256=None,expected_total=None,substitution_path=None):
 root=Path(root).resolve();idl=load(idl_path);program=idl['address'];discs={bytes(x['discriminator']).hex():x['name']for x in idl['instructions']};log_names={re.sub('[^a-z0-9]','',x['name'].lower()):x['name']for x in idl['instructions']}
 assert len(discs)==len(idl['instructions'])==len(log_names)
 inputs={str(Path(p).resolve()):sha(p)for p in [full_path,additional_path,idl_path]};substitutions={};substitution_evidence=[]
 if substitution_path:
  manifest=load(substitution_path);inputs[str(Path(substitution_path).resolve())]=sha(substitution_path)
  if candidate_sha256:assert manifest['candidate_sha256']==candidate_sha256
  for entry in manifest['entries']:
   key=entry['group']+'/'+entry['suite'];assert key not in substitutions
   path=Path(entry['replacement_report']);path=path if path.is_absolute()else root/path;assert sha(path)==entry['replacement_sha256'];inputs[str(path.resolve())]=sha(path)
   replacement=load(path);assert replacement['candidate_sha256']==manifest['candidate_sha256']
   if entry.get('baseline_report'):
    baseline_path=Path(entry['baseline_report']);baseline_path=baseline_path if baseline_path.is_absolute()else root/baseline_path;assert sha(baseline_path)==entry['baseline_sha256'];inputs[str(baseline_path.resolve())]=sha(baseline_path)
   substitutions[key]={'entry':entry,'rows':dict(iter_pairs(replacement)),'used':set()}
 cache={};stats=collections.Counter();groups={};findings=[];attribution=collections.Counter();family=collections.defaultdict(collections.Counter);pair_digests=set();report_candidate=None
 def check_result(result,label):
  encoded=result.get('transaction_base64')
  if not isinstance(encoded,str)or not encoded:
   findings.append({'case':label,'kind':'missing_transaction_bytes'});return None
  try:
   raw=base64.b64decode(encoded,validate=True);digest=hashlib.sha256(raw).hexdigest()
   if digest not in cache:
    tx=VersionedTransaction.from_bytes(raw);required=tx.message.header.num_required_signatures
    assert required>0 and len(tx.signatures)==required,'Signature count does not match message'
    assert all(tx.verify_with_results()),'Invalid cryptographic signature'
    cache[digest]=(tx,[str(k)for k in tx.message.account_keys])
   tx,keys=cache[digest]
   if result.get('transaction_sha256')is not None:assert result['transaction_sha256']==digest,'Recorded transaction hash differs'
   direct=[]
   for index,ix in enumerate(tx.message.instructions):
    assert ix.program_id_index<len(keys),'Top-level program index unresolved'
    if keys[ix.program_id_index]!=program:continue
    data=bytes(ix.data);direct.append({'index':index,'program':program,'discriminator_hex':data[:8].hex(),'name':discs.get(data[:8].hex()),'data_hex':data.hex(),'account_indices':list(ix.accounts)})
   if result.get('instruction_attribution')is not None:assert result['instruction_attribution']=={'main_program':program,'scope':'top_level','main_instructions':direct},'Recorded attribution differs from actual bytes'
   roots=[result[k]for k in ['inner','inner_instructions']if result.get(k)]
   if not roots and isinstance(result.get('metadata'),dict):roots=[result['metadata'][k]for k in ['inner_instructions','innerInstructions']if result['metadata'].get(k)]
   inner=[]
   if roots:
    for path,item in _inner_objects(roots[0]):
     if 'programId'in item:inner_program=item['programId']
     else:
      index=item.get('programIdIndex',item.get('program_id_index'));assert index<len(keys),'Inner program index unresolved';inner_program=keys[index]
     if inner_program!=program:continue
     data=_decode_data(item['data']);inner.append({'path':path,'discriminator_hex':data[:8].hex(),'name':discs.get(data[:8].hex())})
   logged,invocations=_main_logs(result.get('logs',[]),program,log_names);decoded={x['name']for x in direct+inner if x['name']};assert logged<=decoded,('Main log family lacks retained instruction bytes',sorted(logged-decoded))
   if decoded:status='known_main_instruction'
   elif direct or inner:status='unknown_or_malformed_main_instruction'
   elif invocations:raise AssertionError('Main invocation lacks retained main instruction bytes')
   else:status='main_not_invoked'
   attribution[status]+=1
   for name in decoded:family[name]['serialized_result_objects']+=1;family[name]['successful_transaction_results']+=result.get('error')is None
   stats['verified_result_objects']+=1
   return digest,{'status':status,'known_families':sorted(decoded),'main_log_families':sorted(logged),'direct_main_instructions':len(direct),'inner_main_instructions':len(inner)}
  except Exception as exc:
   findings.append({'case':label,'kind':'invalid_or_unattributed_transaction','error':str(exc)});return None
 for group,path in [('full',full_path),('additional',additional_path)]:
  report=load(path);actual_candidate=report['candidate_sha256'];report_candidate=report_candidate or actual_candidate;assert actual_candidate==report_candidate
  if candidate_sha256:assert actual_candidate==candidate_sha256
  n=0;group_stats=collections.Counter()
  for suite,value in report['suites'].items():
   sub=substitutions.get(group+'/'+suite)
   for where,base in iter_pairs(value):
    n+=1;stats['paired_rows']+=1;group_stats['paired_rows']+=1;selected=base
    if sub:
     assert where in sub['rows'],('Substitution row absent',group,suite,where);replacement=sub['rows'][where];sub['used'].add(where)
     assert {k:v for k,v in base.items()if k not in ('original','candidate')}=={k:v for k,v in replacement.items()if k not in ('original','candidate')},'Substitution changes case descriptors'
     for side in ['original','candidate']:
      assert base[side]=={k:v for k,v in replacement[side].items()if k not in ADDED_FIELDS},('Substitution changes pre-existing result fields',group,suite,where,side)
      assert ADDED_FIELDS<=replacement[side].keys(),'Substitution omits receipt fields'
     selected=replacement;stats['substituted_pairs']+=1
    checked=[check_result(selected[side],group+'/'+suite+where+'/'+side)for side in ['original','candidate']]
    if all(checked):
     stats['fully_backed_pairs']+=1;group_stats['fully_backed_pairs']+=1;pair_digests.add((checked[0][0],checked[1][0]))
     if checked[0][0]!=checked[1][0]:findings.append({'case':group+'/'+suite+where,'kind':'original_candidate_transaction_bytes_differ'})
   if sub:
    assert sub['used']==sub['rows'].keys(),'Unconsumed substitution rows';substitution_evidence.append({'group':group,'suite':suite,'rows':len(sub['used']),'replacement_sha256':sub['entry']['replacement_sha256'],'existing_fields_preserved':True,'baseline_report':sub['entry'].get('baseline_report'),'baseline_sha256':sub['entry'].get('baseline_sha256')})
  assert n==report['case_count'],('Declared case count differs',group,n,report['case_count']);assert len(report['suites'])==report['suite_count'];groups[group]=dict(group_stats)
 assert all(x['used']for x in substitutions.values()),'Substitution names an absent suite'
 if expected_total is not None:assert stats['paired_rows']==expected_total
 return {'status':'passed'if not findings else'failed','scope':__doc__,'candidate_sha256':report_candidate,'program':program,'inputs_sha256':inputs,'counts':dict(stats)|{'distinct_signed_transactions':len(cache),'distinct_transaction_pairs':len(pair_digests)},'groups':groups,'main_attribution':dict(attribution),'families':{k:dict(v)for k,v in sorted(family.items())},'findings':findings,'substitutions':substitution_evidence,'limitations':['Known instruction bytes do not establish branch coverage.','Unknown/malformed main payloads remain classified by retained bytes.','A verified outer transaction rejected before a main call is recorded as main_not_invoked, not as main-family execution.','No transaction was constructed, signed, submitted or executed.']}
