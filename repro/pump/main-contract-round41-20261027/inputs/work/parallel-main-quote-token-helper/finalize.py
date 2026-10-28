from pathlib import Path
import base64,difflib,gzip,hashlib,json
from solders.transaction import Transaction
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;S=P/'source01';B=R/'work/parallel-main-sweep-recipient-reuse/source01';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
b=json.load(open(P/'build01/build-comparison.json'));candidate=sha(P/'build01/candidate.so');original='7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d';assert b['source_unchanged'] and candidate==b['comparison']['candidate_sha256']
reports=[json.load(open(P/'after01-full-summary.json')),json.load(open(P/'after01-focused-summary.json'))];summaries=[];transactions=loads=cases=strict=0
for report in reports:
 for suite in report['results']:
  assert suite['returncode']==0 and not suite['mismatches'] and not suite['strict_mismatches']
  data=json.load(gzip.open(R/suite['archive'],'rt'));assert data['candidate_sha256']==candidate
  sets=data.get('suites') or {'waiver':data['cases']};rr=[r for vs in sets.values() for r in vs]
  for row in rr:
   assert not row['different_fields'] and row['original']['transaction_base64']==row['candidate']['transaction_base64']
   for side in ['original','candidate']:Transaction.from_bytes(base64.b64decode(row[side]['transaction_base64'])).verify();transactions+=1
   if 'loader' in row:
    assert [l['elf_sha256'] for l in row['loader']]==[original,candidate]
    assert all(l['elf_prefix_unchanged'] and l['zero_allocation_tail'] for l in row['loader']);loads+=len(row['loader'])
  if suite['suite']=='waiver':
   ls=json.load(open(R/suite['loader_receipt']))['loads'];assert len([l for l in ls if l['elf_sha256']==candidate])==len(rr);assert all(l['elf_prefix_unchanged'] and l['zero_allocation_tail'] for l in ls);loads+=2*len(rr)
  cases+=len(rr);strict+=suite['strict_case_count'];summaries.append({k:suite[k] for k in ['suite','case_count','strict_case_count','archive','archive_sha256']})
r=json.load(gzip.open(P/'after01-sweeps.json.gz','rt'));assert r['candidate_sha256']==candidate and not r['mismatches'] and not r['diagnostics']['mismatches'];rr=r['suites']['sweeps']
for row in rr:
 assert not row['different_fields'] and row['original']['transaction_base64']==row['candidate']['transaction_base64']
 for side in ['original','candidate']:Transaction.from_bytes(base64.b64decode(row[side]['transaction_base64'])).verify();transactions+=1
 assert [l['elf_sha256'] for l in row['loader']]==[original,original,candidate];assert all(l['elf_prefix_unchanged'] and l['zero_allocation_tail'] for l in row['loader']);loads+=3
cases+=len(rr);strict+=r['diagnostics']['log_bearing_cases'];summaries.append({'suite':'sweeps','case_count':len(rr),'strict_case_count':r['diagnostics']['log_bearing_cases'],'archive':str((P/'after01-sweeps.json.gz').relative_to(R)),'archive_sha256':sha(P/'after01-sweeps.json.gz')})
assert (cases,strict,transactions,loads)==(2150,2148,4300,4762)
files=['src/sell_v2.rs','src/sweep_fees.rs','src/v2_quote_token_transfers.rs'];actual=[str(p.relative_to(S)) for p in S.rglob('*') if p.is_file() and (not (B/p.relative_to(S)).exists() or p.read_bytes()!=(B/p.relative_to(S)).read_bytes())];assert set(actual)==set(files)
patch=''
for f in files:
 old=(B/f).read_text().splitlines(True) if (B/f).exists() else []
 patch+=''.join(difflib.unified_diff(old,(S/f).read_text().splitlines(True),fromfile='a/programs/pump/'+f if old else '/dev/null',tofile='b/programs/pump/'+f));assert b['primary_source_sha256'][str((S/f).relative_to(R))]==sha(S/f)
(P/'quote-token-helper.patch').write_text(patch)
e=json.load(open(P/'EXACT-EVIDENCE.json'));x={'status':'validated frozen genuine quote-token CPI helper','source':str(S.relative_to(R)),'base':str(B.relative_to(R)),'files':{f:sha(S/f) for f in files},'patch':str((P/'quote-token-helper.patch').relative_to(R)),'candidate_sha256':candidate,'unstripped_sha256':sha(P/'build01/unstripped.so'),'original_sha256':original,'source_build_binding':True,'case_count':cases,'strict_case_count':strict,'verified_transaction_signatures':transactions,'paired_comparison_loads':2*cases,'per_case_program_loads':loads,'extra_original_fixture_loads':len(rr),'suites':summaries,'helper':e,'new_behavioral_counterexamples':0,'scope':'Restore original liveCPIboundary/ABI; no behavioral change intended. Exacthelper plus existing token2022 transfer_checked callee, realSellV2/Sweep callers.','full_elf_identity':False};(P/'summary.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:x[k] for k in ['files','candidate_sha256','unstripped_sha256','case_count','strict_case_count','verified_transaction_signatures','per_case_program_loads']},indent=2))
