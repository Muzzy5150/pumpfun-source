from pathlib import Path
import base64,bisect,difflib,gzip,hashlib,json,struct,sys,csv
from solders.transaction import Transaction
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;sys.path.insert(0,str(R/'scripts'))
from pump_compare_function_bytes import body,normalize
from pump_quote_control_function_match import sections,candidate_functions
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=json.load(open(P/'after01-focused-summary.json'));a=json.load(open(P/'after01-full-summary.json'));b=json.load(open(P/'build01/build-comparison.json'))
assert b['returncode']==0 and b['source_unchanged']
elf=P/'build01/candidate.so';unstrip=P/'build01/unstripped.so';candidate_sha=SHA(elf);original_sha='7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d'
assert candidate_sha==b['comparison']['candidate_sha256'] and SHA(unstrip)==b['unstripped_sha256']
signed=loads=0;counts=[]
for suite in f['results']+a['results']:
 assert suite['returncode']==0 and not suite['mismatches'] and not suite['strict_mismatches'],suite
 path=R/suite['archive'];assert SHA(path)==suite['archive_sha256'];x=json.load(gzip.open(path,'rt'));assert x['candidate_sha256']==candidate_sha
 rows=[row for values in x['suites'].values() for row in values] if 'suites' in x else x['cases']
 for row in rows:
  assert not row['different_fields'];assert row['original']['transaction_base64']==row['candidate']['transaction_base64']
  for result in [row['original'],row['candidate']]:Transaction.from_bytes(base64.b64decode(result['transaction_base64'])).verify();signed+=1
  if 'loader' in row:
   assert len(row['loader'])==2
   for expected,load in zip([original_sha,candidate_sha],row['loader']):assert load['elf_sha256']==expected and load['elf_prefix_unchanged'] and load['zero_allocation_tail'];loads+=1
 if suite['suite']=='waiver':
  ls=json.load(open(R/suite['loader_receipt']))['loads'];assert len([l for l in ls if l['elf_sha256']==candidate_sha])==len(rows)
  assert all(l['elf_sha256'] in [candidate_sha,original_sha] and l['elf_prefix_unchanged'] and l['zero_allocation_tail'] for l in ls);loads+=len(rows)*2
 counts.append({k:suite[k] for k in ['suite','case_count','strict_case_count','archive','archive_sha256','script','script_sha256']})
assert signed==3376 and loads==3376
report={'case_count':f['cases']+a['cases'],'strict_case_count':f['strict_cases']+a['strict_cases'],'paired_captured_loads':loads,'verified_transaction_signatures':signed,'candidate_sha256':candidate_sha,'suites':counts}
(P/'RUNTIME-RESULT.json').write_text(json.dumps(report,indent=2)+'\n');
print(json.dumps({k:report[k] for k in ['candidate_sha256','case_count','strict_case_count']},indent=2))
