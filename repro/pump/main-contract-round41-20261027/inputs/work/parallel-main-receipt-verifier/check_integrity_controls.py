"""Offline integrity controls over copies of a captured receipt. No VM or transaction construction."""
from pathlib import Path
import base64,copy,hashlib,json
from receipt_verifier import verify_reports,load,ADDED_FIELDS
P=Path(__file__).resolve().parent;R=P.parents[1];C=P/'controls';C.mkdir(exist_ok=True)
record=load(R/'work/parallel-main-receipt-capture/run02/full.volume.json.gz');row=record['cases'][0];candidate=record['candidate_sha256'];idl=R/'evidence/upstream/pump.json'
def write(name,x):
 path=C/(name+'.json');path.write_text(json.dumps(x,sort_keys=True)+'\n');return path
additional=write('additional',{'candidate_sha256':candidate,'case_count':0,'suite_count':0,'suites':{}})
def full(value):return {'candidate_sha256':candidate,'case_count':1,'suite_count':1,'suites':{'fixture':{'cases':[value]}}}
def check(name,value,passed=False,substitution=None,expected=None):
 path=write(name,full(value));outcome={}
 try:
  result=verify_reports(path,additional,idl,root=R,expected_total=1,substitution_path=substitution,candidate_sha256=candidate);actual=result['status']=='passed';outcome={'accepted':actual,'findings':result['findings']}
 except Exception as exc:actual=False;outcome={'accepted':False,'error':str(exc)}
 assert actual==passed,(name,outcome)
 if expected:assert any(expected in str(x)for x in outcome.get('findings',[]))or expected in outcome.get('error',''),(name,outcome)
 return {'name':name,**outcome}
results=[check('positive',row,True)]
x=copy.deepcopy(row);del x['original']['transaction_base64'];results.append(check('missing_bytes',x,expected='missing_transaction_bytes'))
x=copy.deepcopy(row);x['candidate']['transaction_sha256']='0'*64;results.append(check('wrong_tx_hash',x,expected='transaction hash differs'))
x=copy.deepcopy(row);x['candidate']['instruction_attribution']['main_program']='wrong';results.append(check('wrong_attribution',x,expected='attribution differs'))
x=copy.deepcopy(row);raw=bytearray(base64.b64decode(x['candidate']['transaction_base64']));raw[1]^=1;x['candidate']['transaction_base64']=base64.b64encode(raw).decode();x['candidate']['transaction_sha256']=hashlib.sha256(raw).hexdigest();results.append(check('invalid_signature',x,expected='Invalid cryptographic signature'))
base=copy.deepcopy(row)
for side in ['original','candidate']:
 for key in ADDED_FIELDS:base[side].pop(key,None)
replacement=write('replacement',{'candidate_sha256':candidate,'cases':[row]});sub={'candidate_sha256':candidate,'entries':[{'group':'full','suite':'fixture','replacement_report':str(replacement),'replacement_sha256':hashlib.sha256(replacement.read_bytes()).hexdigest()}]};sub_path=write('substitution',sub);results.append(check('positive_substitution',base,True,sub_path))
bad=copy.deepcopy(row);bad['original']['error']='changed pre-existing field';replacement2=write('replacement_bad',{'candidate_sha256':candidate,'cases':[bad]});sub['entries'][0]['replacement_report']=str(replacement2);sub['entries'][0]['replacement_sha256']=hashlib.sha256(replacement2.read_bytes()).hexdigest();bad_sub=write('substitution_bad_field',sub);results.append(check('altered_old_field',base,False,bad_sub,expected='pre-existing result fields'))
sub['entries'][0]['replacement_sha256']='0'*64;bad_hash=write('substitution_bad_hash',sub);results.append(check('altered_substitution_hash',base,False,bad_hash))
out={'status':'passed','controls':results,'source_receipt':'work/parallel-main-receipt-capture/run02/full.volume.json.gz','source_sha256':hashlib.sha256((R/'work/parallel-main-receipt-capture/run02/full.volume.json.gz').read_bytes()).hexdigest(),'transactions_constructed_or_executed':0};(P/'INTEGRITY-CONTROLS.json').write_text(json.dumps(out,indent=2)+'\n');print({'controls':len(results),'passed':True,'transactions_executed':0})
