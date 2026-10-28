from pathlib import Path
import base64,bisect,difflib,gzip,hashlib,json,struct,sys,csv
from solders.transaction import Transaction
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;sys.path.insert(0,str(R/'scripts'))
from pump_compare_function_bytes import body,normalize
from pump_quote_control_function_match import sections,candidate_functions
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=json.load(open(P/'after01-focused-summary.json'));a=json.load(open(P/'after01-full-summary.json'));b=json.load(open(P/'build02/build-comparison.json'))
assert b['returncode']==0 and b['source_unchanged']
elf=P/'build02/candidate.so';unstrip=P/'build02/unstripped.so';candidate_sha=SHA(elf);original_sha='7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d'
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
changed=[str(p.relative_to(P/'source01')) for p in (P/'source01').rglob('*') if p.is_file() and p.read_bytes()!=(P/'source-base'/p.relative_to(P/'source01')).read_bytes()];assert changed==['src/sell_v2.rs']
name='src/sell_v2.rs';digest=SHA(P/'source01'/name);assert b['primary_source_sha256'][str((P/'source01'/name).relative_to(R))]==digest
iv=json.load(open(P/'inventory01.json'));base=json.load(open(R/'work/parallel-main-integration/build-round21/normalized-inventory.json'));matches=lambda x:{r['start'] for r in x['windows'] if r['normalized_matches']};gain=matches(iv)-matches(base);lost=matches(base)-matches(iv)
assert gain=={0x9a048} and not lost
orig=(R/'evidence/original/pump/deployed.so').read_bytes();cand=unstrip.read_bytes();os=sections(orig);cs=sections(cand);lens={int(r['original_start']):int(r['bytes']) for r in csv.DictReader(open(R/'repro/reconstruction-status-2026-10-26/functions.tsv'),delimiter='\t') if r['program']=='pump'}
proof={}
for file in ['split-comparison01.json','user-transfer-comparison01.json']:
 comp=json.load(open(P/file));h=comp['candidates'][0];assert h['normalized_equal'];calls=[]
 for x,y in zip([x for x in comp['original_operands'] if x['kind']=='direct-call'],[x for x in h['operands'] if x['kind']=='direct-call']):
  n=lens[x['target']];eq=normalize(body(orig,os,x['target'],n),x['target'],os)[0]==normalize(body(cand,cs,y['target'],n),y['target'],cs)[0];assert eq
  calls.append({'offset':x['offset'],'original':hex(x['target']),'candidate':hex(y['target']),'bytes':n,'normalized_equal':eq})
 proof[hex(comp['original_start'])]={'candidate':hex(h['start']),'bytes':h['bytes'],'normalized_equal':True,'callees':calls}
new=[]
for s in f['results']:
 if s['suite'] not in ['sell-v2-split','sell-v2-thresholds']:continue
 new.append({'name':s['suite'],'cases':s['case_count'],'script':s['script'],'script_sha256':s['script_sha256'],'command':['work/test-env/bin/python',s['script'],'--candidate','CANDIDATE','--output',s['suite']+'.json.gz'],'archive':s['archive'],'archive_sha256':s['archive_sha256']})
(P/'NEW-CASES.json').write_text(json.dumps({'case_count':66,'strict_cases':66,'suites':new},indent=2)+'\n')
report={'status':'validated frozen SellV2 buyback/payment delivery','source':str((P/'source01').relative_to(R)),'base':str((P/'source-base').relative_to(R)),'base_composition':'frozen Round21 plus four unchanged files from accepted legacy buyback source03','files':{name:digest},'patch':str((P/'sell-v2-payment-order.patch').relative_to(R)),'candidate_sha256':candidate_sha,'unstripped_sha256':SHA(unstrip),'original_sha256':original_sha,'case_count':f['cases']+a['cases'],'strict_case_count':f['strict_cases']+a['strict_cases'],'paired_captured_loads':loads,'verified_transaction_signatures':signed,'source_build_binding':True,'inventory':iv['counts'],'normalized_gains_vs_round21':[hex(x) for x in sorted(gain)],'normalized_losses_vs_round21':[],'gain_attribution':'0x9a048 was already accepted via preceding V2/legacy helper delivery; this change adds its final real SellV2 caller, no separate new body match','preserved_exact_helpers':proof,'suites':counts,'full_elf_identity':False,'new_cases':'NEW-CASES.json','before_failures':{'sell-v2-split':4,'sell-v2-thresholds':16},'failed_control':'build01 cold old-registry dependency build ended ENFILE/os23; build02 used verified current cache and freshly compiled main source'}
(P/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['files','candidate_sha256','unstripped_sha256','case_count','strict_case_count','inventory']},indent=2))
