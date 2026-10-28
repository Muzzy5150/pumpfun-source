"""Signed original/candidate checks for structured error-origin fields and ordering."""
from pathlib import Path
import sys,types,argparse,hashlib,json,re,base64,gzip
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from solders.transaction import Transaction
import pump_migrate_v2_probe as migration
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()

def load_prefix(path,name):
 scope={'__file__':str(path),'__name__':name};code=path.read_text().split('\nrows=[]',1)[0];exec(compile(code,str(path),'exec'),scope);return scope
reserved=load_prefix(ROOT/'work/parallel-main-origins/probe_recipients.py','reserved_adapter')['module']
params=load_prefix(ROOT/'work/parallel-main-origins/probe_set_params.py','params_adapter')['m']

def diag(x):
 out=[]
 for line in x['logs']:
  if 'AnchorError' in line:out.append(re.sub(r' thrown in .*?:\d+\.', '.',line))
  elif line.startswith(('Program log: Left:','Program log: Right:')):out.append(line)
 return out
rows=[]
def compare(name,c,a,b,fields):
 different=[k for k in fields if a[k]!=b[k]]
 if diag(a)!=diag(b):different.append('error_origin_and_comparison')
 assert a['transaction_base64']==b['transaction_base64'];Transaction.from_bytes(base64.b64decode(a['transaction_base64'])).verify()
 rows.append({'name':name,'case':c,'original':a,'candidate':b,'different_fields':different})
for index in range(8):
 for mut in [f'at_program_{index}',f'at_rent_{index}_0',f'at_rent_{index}_890879']:
  a=reserved.execute(ROOT/'evidence/original/pump/deployed.so','set_reserved_fee_recipients',bytes([55])*32,mut);b=reserved.execute(args.candidate,'set_reserved_fee_recipients',bytes([55])*32,mut)
  compare('reserved-'+mut,{'mutation':mut},a,b,['error','data_hex','lamports','payer_lamports','authority_lamports','event_payloads','inner_instructions'])
for index in range(8):
 c={'recipient_index':index,'recipient_lamports':0};a=params.run(c);b=params.run(c,args.candidate);compare('fee-recipient-'+str(index),c,a,b,['error','before','after','events','inner','returns'])
for mode in [{},{'stable':True},{'stable':True,'quote22':True}]:
 for extra in [{},{'complete':0},{'enable_migrate':0},{'mutations':{'bonding_curve':{'patches':[(i,bytes(8).hex()) for i in [8,16,24,32]]}}},{'mutations':{'global':{'patches':[(0,bytes(8).hex())]}}}]:
  c={'boost':True,'wrong':'pump_amm_event_authority',**mode,**extra};a=migration.run(c);b=migration.run(c,args.candidate);fields=[k for k in ['error','before','after','inner','return'] if k in a and k in b];compare('event-'+str(len(rows)),c,a,b,fields)
result={'scope':__doc__,'candidate_sha256':hashlib.sha256(args.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'case_count':len(rows),'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'cases':rows};args.output.write_bytes(gzip.compress(json.dumps(result,indent=2).encode(),mtime=0));print({'case_count':len(rows),'mismatches':result['mismatches']});assert not result['mismatches']
