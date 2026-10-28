from pathlib import Path
import base64,difflib,gzip,hashlib,json
from solders.transaction import Transaction
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def matched(d,k):return sorted(w['start']for w in d['windows']if w[k])
base=P/'source-metadata-data-first';src=P/'source-v2-metadata-combined';build=P/'build-v2-metadata-combined';br=read(build/'build-comparison.json');v=read(P/'v2-metadata-combined-runtime/summary.json');a=read(P/'build-metadata-data-first/normalized-inventory.json');b=read(build/'normalized-inventory.json')
assert v['case_count']==517 and not v['errors']and not v['diagnostics']['mismatches'];assert br['source_unchanged'];assert sha(build/'candidate.so')==br['comparison']['candidate_sha256']==v['candidate_sha256'];assert sha(build/'unstripped.so')==br['unstripped_sha256'];assert all(sha(k)==h for k,h in v['input_sha256'].items())
changes=[]
for f in base.rglob('*'):
 if f.is_file() and f.suffix in ['.rs','.toml','.lock'] and sha(f)!=sha(src/f.relative_to(base)):changes.append(str(f.relative_to(base)))
assert changes==['src/create_v2.rs'],changes
old=matched(a,'normalized_matches');new=matched(b,'normalized_matches');oldraw=matched(a,'raw_match');newraw=matched(b,'raw_match');g=sorted(set(new)-set(old));assert len(g)==11 and not set(old)-set(new)and not set(oldraw)-set(newraw)
leaf=[0x9b6a0,0x9bc28,0x9c240,0x9c8f8,0x9d008,0x9d850,0x9e178,0x9eaf0,0x9f500];assert set(leaf)<=set(new)
assert all(f['candidate']['normalized_equal']for f in read(build/'function-comparison.json')['functions'])
patch=P/'v2-metadata-combined-from-data-first.patch';patch.write_text(''.join(difflib.unified_diff((base/'src/create_v2.rs').read_text().splitlines(True),(src/'src/create_v2.rs').read_text().splitlines(True),fromfile='a/programs/pump/src/create_v2.rs',tofile='b/programs/pump/src/create_v2.rs')))
txs=set()
def collect(o):
 if isinstance(o,dict):
  for k,x in o.items():
   if k=='transaction_base64'and x:txs.add(x)
   elif isinstance(x,(dict,list)):collect(x)
 elif isinstance(o,list):
  for x in o:collect(x)
counts=[]
for row in v['results']:
 n=row['name'];r=read(P/'v2-metadata-combined-runtime'/(n+'.json.gz'));collect(r);l=read(P/'v2-metadata-combined-runtime'/(n+'.loader.json'));assert {x['elf_sha256']for x in l['loads']}=={br['comparison']['candidate_sha256'],br['comparison']['original_sha256']};counts.append({'name':n,'cases':row['cases'],'receipt_sha256':row['result_sha256'],'loader_sha256':row['loader_sha256'],'captured_loads':len(l['loads'])})
for t in txs:assert all(Transaction.from_bytes(base64.b64decode(t)).verify_with_results())
r={'status':'passed, frozen','scope':'Main-Pump CreateV2 uses existing typed Token2022 metadata initialize/clear-authority CPIs and actual TokenMetadata Borsh packed-size calculation. Only create_v2.rs differs from accepted DATA-FIRST; no dependency or companion source edits.','baseline_source':str(base),'source':str(src),'build_source':br['source_directory'],'base_create_v2_sha256':sha(base/'src/create_v2.rs'),'source_create_v2_sha256':sha(src/'src/create_v2.rs'),'patch':str(patch),'patch_sha256':sha(patch),'candidate_sha256':sha(build/'candidate.so'),'unstripped_sha256':sha(build/'unstripped.so'),'build_receipt_sha256':sha(build/'build-comparison.json'),'baseline_counts':a['counts'],'counts':b['counts'],'baseline_normalized_windows':old,'normalized_windows':new,'normalized_gained':g,'normalized_lost':[],'baseline_raw_windows':oldraw,'raw_windows':newraw,'raw_gained':sorted(set(newraw)-set(oldraw)),'raw_lost':[],'preserved_historical_decoder_windows':leaf,'all6_creation_parser_wrapper_exit_bodies_retained':True,'validation':{'cases':517,'strict_diagnostic_pairs':v['diagnostics']['log_bearing_cases'],'distinct_signed_transactions_reverified':len(txs),'captured_loads':sum(r['captured_loads']for r in counts),'summary_sha256':sha(P/'v2-metadata-combined-runtime/summary.json'),'suites':counts},'remaining':'Creation business handler bodies and several main-owned metadata setup helpers remain unmatched. Full ELF equality is not claimed.'}
(P/'V2-METADATA-COMBINED-REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'review_sha256':sha(P/'V2-METADATA-COMBINED-REVIEW.json'),'source_sha256':r['source_create_v2_sha256'],'patch_sha256':r['patch_sha256'],'candidate_sha256':r['candidate_sha256'],'unstripped_sha256':r['unstripped_sha256'],'counts':r['counts'],'validation':{k:x for k,x in r['validation'].items()if k!='suites'}},indent=2))
