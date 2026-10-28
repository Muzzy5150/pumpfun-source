#!/usr/bin/env python3
"""Keep signed receipts for the existing19 update-global-authority fixtures.

Only signature checks and returned receipt fields are added to the exact current
fixture function; VM inputs and execution logic are unchanged.
"""
from pathlib import Path
import ast,copy,argparse,hashlib,json,gzip,base64
ROOT=Path(__file__).resolve().parents[2];H=ROOT/'scripts/pump_validate_authority.py'
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
tree=ast.parse(H.read_text());head=[]
for node in tree.body:
 if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='p'for t in node.targets):break
 head.append(node)
ns={'__name__':'authority_receipt_fixture','__file__':str(H)};exec(compile(ast.Module(body=head,type_ignores=[]),str(H),'exec'),ns)
f=copy.deepcopy(next(x for x in head if isinstance(x,ast.FunctionDef)and x.name=='execute'));f.name='execute_with_receipts';ret=next(i for i,n in enumerate(f.body)if isinstance(n,ast.Return));f.body[ret:ret]=ast.parse("result['transaction_base64'] = base64.b64encode(bytes(tx)).decode()\nresult['signature_verification'] = tx.verify_with_results()\nassert all(result['signature_verification'])").body;exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),str(Path(__file__)),'exec'),ns)
mutations=['none','global_owner','global_discriminator','global_truncated','global_address','global_readonly','authority_readonly','authority_unsigned','authority_wrong','event_wrong','program_wrong','missing_event','missing_program','initialized_invalid','length_1087','length_1088','new_zero','new_same']
rows=[];before={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [H,a.candidate,Path(__file__),ROOT/'evidence/original/pump/deployed.so']}
for m,payload in [(m,b'')for m in mutations]+[('trailing',b'\xff')]:
 x=ns['execute_with_receipts'](ROOT/'evidence/original/pump/deployed.so','update_global_authority',payload,'none'if m=='trailing'else m);y=ns['execute_with_receipts'](a.candidate,'update_global_authority',payload,'none'if m=='trailing'else m)
 fields=[k for k in x if k!='logs'];diff=[k for k in fields if x[k]!=y[k]];rows.append({'case':m,'original':x,'candidate':y,'different_fields':diff})
assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [H,a.candidate,Path(__file__),ROOT/'evidence/original/pump/deployed.so']}
j={'scope':__doc__,'inputs_sha256':before,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows)if r['different_fields']],'cases':rows};a.output.write_bytes(gzip.compress(json.dumps(j,separators=(',',':')).encode(),mtime=0));print({'case_count':len(rows),'mismatches':j['mismatches']});assert not j['mismatches']
