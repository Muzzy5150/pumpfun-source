from pathlib import Path
import base64,gzip,hashlib,json,sys
from solders.transaction import Transaction
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=json.load(open(P/'after03-focused-summary.json'));a=json.load(open(P/'after03-summary.json'));assert f['mode']=='focused' and a['mode']=='full';(P/'after03-full-summary.json').write_text(json.dumps(a,indent=2)+'\n')
b=json.load(open(P/'build04/build-attempt.json'));assert b['returncode']==0 and b['source_unchanged'];h=json.load(open(P/'EXACT-EVIDENCE.json'));assert not h['gained'] and not h['lost'];candidate_sha=h['candidate_sha256'];original_sha='7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d'
signed=0;loads=0;counts=[]
for suite in f['results']+a['results']:
 assert not suite.get('archive_missing') and suite['returncode']==0 and not suite['mismatches'] and not suite['strict_mismatches'],suite
 path=R/suite['archive'];assert SHA(path)==suite['archive_sha256'];x=json.load(gzip.open(path,'rt'));assert x['candidate_sha256']==candidate_sha
 rows=[row for values in x['suites'].values() for row in values] if 'suites' in x else x['cases']
 for row in rows:
  assert not row['different_fields'];assert row['original']['transaction_base64']==row['candidate']['transaction_base64']
  for result in [row['original'],row['candidate']]:
   tx=Transaction.from_bytes(base64.b64decode(result['transaction_base64']));tx.verify();signed+=1
  if 'loader' in row:
   assert len(row['loader'])==2
   for expected,load in zip([original_sha,candidate_sha],row['loader']):
    assert load['elf_sha256']==expected and load['elf_prefix_unchanged'] and load['zero_allocation_tail'];loads+=1
 if suite['suite']=='waiver':
  ls=json.load(open(R/suite['loader_receipt']))['loads'];n=[l for l in ls if l['elf_sha256']==candidate_sha];assert len(n)==len(rows)
  assert all(l['elf_sha256'] in [candidate_sha,original_sha] and l['elf_prefix_unchanged'] and l['zero_allocation_tail'] for l in ls)
  loads+=len(rows)*2
 counts.append({k:suite[k] for k in ['suite','case_count','strict_case_count','archive','archive_sha256','script','script_sha256']})
for name,digest in h['files'].items():
 assert SHA(P/'source03'/name)==digest
 assert b['primary_source_sha256'][str((P/'source03'/name).relative_to(R))]==digest
assert signed==3244 and loads==3244
new=[]
for s in f['results']:
 cmd=['work/test-env/bin/python',s['script'],'--candidate','CANDIDATE','--output',s['suite']+'.json.gz']
 new.append({'name':s['suite'],'cases':s['case_count'],'script':s['script'],'script_sha256':s['script_sha256'],'command':cmd,'archive':s['archive'],'archive_sha256':s['archive_sha256']})
(P/'NEW-CASES.json').write_text(json.dumps({'case_count':f['cases'],'strict_cases':f['strict_cases'],'suites':new,'excluded_failed_probe':'probe-sell-creator-order.py lacked a preseeded normal empty creator vault; no receipt produced. Corrected immutable probe-sell-creator-order02.py is validated.'},indent=2)+'\n')
h.update(status='validated frozen legacy buyback/payment delivery',patch='work/parallel-main-legacy-buyback-split/legacy-buyback-split.patch',case_count=f['cases']+a['cases'],strict_case_count=f['strict_cases']+a['strict_cases'],paired_captured_loads=loads,verified_transaction_signatures=signed,suites=counts,source_build_binding=True,full_elf_identity=False,helper_normalized_different_slots=0,new_cases='work/parallel-main-legacy-buyback-split/NEW-CASES.json',before_positive_cases={'legacy_boundary':7,'low_lamports':2,'partial_balance':1,'payment_thresholds':2,'creator_order':3})
(P/'summary.json').write_text(json.dumps(h,indent=2)+'\n')
print(json.dumps({k:h[k] for k in ['case_count','strict_case_count','paired_captured_loads','verified_transaction_signatures','files','candidate_sha256','unstripped_sha256','inventory','gained','lost']},indent=2))
