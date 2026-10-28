from pathlib import Path
import json,hashlib,gzip,difflib,base64,sys
ROOT=Path(__file__).resolve().parents[2]
P=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from solders.transaction import Transaction
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def matched(d,k):return sorted(w['start']for w in d['windows']if w[k])
a=read(P/'build-static-metadata-seed/normalized-inventory.json');b=read(P/'build-option-read-exact/normalized-inventory.json');r=read(P/'option-read-exact-runtime/summary.json');br=read(P/'build-option-read-exact/build-comparison.json')
assert r['case_count']==832 and not r['errors'] and not r['diagnostics']['mismatches']
assert br['returncode']==0 and br['source_unchanged'] and br['comparison']['candidate_sha256']==sha(P/'build-option-read-exact/candidate.so')==r['candidate_sha256']
assert all(sha(ROOT/k)==v for k,v in br['source_sha256'].items())
assert all(sha(k)==v for k,v in r['input_sha256'].items())
before=P/'source-static-metadata-seed';after=P/'source-option-read-exact';changed=[]
for f in sorted(before.rglob('*')):
 if f.is_file() and f.suffix in ['.rs','.toml','.lock'] and sha(f)!=sha(after/f.relative_to(before)):changed.append(str(f.relative_to(before)))
assert changed==['src/lib.rs'],changed
patch=P/'option-bool-read-exact.patch';patch.write_text(''.join(difflib.unified_diff((before/'src/lib.rs').read_text().splitlines(True),(after/'src/lib.rs').read_text().splitlines(True),fromfile='a/programs/pump/src/lib.rs',tofile='b/programs/pump/src/lib.rs')))
ng=sorted(set(matched(b,'normalized_matches'))-set(matched(a,'normalized_matches')));nl=sorted(set(matched(a,'normalized_matches'))-set(matched(b,'normalized_matches')));rg=sorted(set(matched(b,'raw_match'))-set(matched(a,'raw_match')));rl=sorted(set(matched(a,'raw_match'))-set(matched(b,'raw_match')))
assert ng==[0x8b818,0x1268a8] and not nl and not rg and not rl,(ng,nl,rg,rl)
retained=[0x127510,0x127b58,0x1286c8,0x128c28,0x9b6a0,0x9bc28,0x9c240,0x9c8f8,0x9d008,0x9d850,0x9e178,0x9eaf0,0x9f500]
assert set(retained)<=set(matched(b,'normalized_matches'))
txs=set()
def scan(o):
 if isinstance(o,dict):
  for k,v in o.items():
   if k=='transaction_base64' and v:txs.add(v)
   elif isinstance(v,(dict,list)):scan(v)
 elif isinstance(o,list):
  for x in o:scan(x)
case_receipts=[]
for result in r['results']:
 name=result['name'];file=P/'option-read-exact-runtime'/(name+'.json.gz');receipt=read(file);scan(receipt);loader=P/'option-read-exact-runtime'/(name+'.loader.json');lr=read(loader)
 assert {x['elf_sha256']for x in lr['loads']}=={br['comparison']['candidate_sha256'],br['comparison']['original_sha256']}
 case_receipts.append({'name':name,'cases':result['cases'],'receipt_sha256':sha(file),'loader_sha256':sha(loader),'captured_loads':len(lr['loads'])})
for t in txs:assert all(Transaction.from_bytes(base64.b64decode(t)).verify_with_results())
functions=read(P/'build-option-read-exact/function-comparison.json')['functions'];assert all(f['candidate']['normalized_equal']for f in functions)
report={'status':'passed','scope':'Main-Pump OptionBool uses one-byte read_exact with UnexpectedEof=false and unchanged dynamic invalid-byte InvalidData error. No dependency, companion, or shared canonical source edits.','baseline':'Round16 plus accepted Create +7 and static-metadata +1','baseline_source':str(before),'source':str(after),'build_source':br['source_directory'],'base_file_sha256':sha(before/'src/lib.rs'),'source_file_sha256':sha(after/'src/lib.rs'),'changed_files':changed,'patch':str(patch),'patch_sha256':sha(patch),'candidate_sha256':sha(P/'build-option-read-exact/candidate.so'),'unstripped_sha256':sha(P/'build-option-read-exact/unstripped.so'),'build_receipt_sha256':sha(P/'build-option-read-exact/build-comparison.json'),'baseline_counts':a['counts'],'counts':b['counts'],'baseline_normalized_windows':matched(a,'normalized_matches'),'normalized_windows':matched(b,'normalized_matches'),'normalized_gained':ng,'normalized_lost':nl,'baseline_raw_windows':matched(a,'raw_match'),'raw_windows':matched(b,'raw_match'),'raw_gained':rg,'raw_lost':rl,'retained_buy_wrappers_and_historical_decoders':retained,'creation_functions':[{k:f[k]for k in ['label','original_start','original_bytes']}|{'candidate_start':f['candidate']['start'],'candidate_bytes':f['candidate']['bytes'],'normalized_equal':f['candidate']['normalized_equal']}for f in functions],'validation':{'summary':str(P/'option-read-exact-runtime/summary.json'),'summary_sha256':sha(P/'option-read-exact-runtime/summary.json'),'cases':832,'strict_diagnostic_pairs':r['diagnostics']['log_bearing_cases'],'distinct_transactions_reverified':len(txs),'captured_loads':sum(x['captured_loads']for x in case_receipts),'receipts':case_receipts},'reason':'Original shared OptionBool decoder directly consumes one byte on nonempty input. read() generated min(len,1) state; read_exact() matches the fixed one-byte path. The complete344B decoder and3176B CreateV2 wrapper now match.','limitations':'Validation concerns actual transaction byte-slice decoding, including empty reads and invalid bytes. No claim is made about arbitrary custom Read implementations. Whole ELF remains unequal.'}
(P/'OPTION-BOOL-REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'review_sha256':sha(P/'OPTION-BOOL-REVIEW.json'),'patch_sha256':sha(patch),'candidate_sha256':report['candidate_sha256'],'unstripped_sha256':report['unstripped_sha256'],'cases':832,'strict_pairs':r['diagnostics']['log_bearing_cases'],'transactions':len(txs),'counts':b['counts']},indent=2))
