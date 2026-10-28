from pathlib import Path
import json,gzip,hashlib,sys,shutil,difflib
sys.path.insert(0,'scripts');from pump_diagnostic_audit import audit
P=Path(__file__).parent;src=P/'raw-authority-source';b=P/'raw-authority-build';base=Path('work/parallel-main-integration/round20-source/programs/pump')
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def read(f):
 r=f.read_bytes();return json.loads(gzip.decompress(r)if r[:2]==b'\x1f\x8b'else r)
state=read(P/'raw-regression-state.json');assert len(state)==21 and all(r['returncode']==0 for r in state.values());reports={k:read(Path(v['output']))for k,v in state.items()};counts={k:v['case_count']for k,v in reports.items()};assert sum(counts.values())==1145
ch=sha(b/'candidate.so');original='7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d'
def verify(v):
 if isinstance(v,dict):
  assert not v.get('different_fields')and not v.get('mismatches')and v.get('match')is not False
  for k,x in v.items():
   if k not in ('original','candidate'):verify(x)
 elif isinstance(v,list):
  for x in v:verify(x)
for k,r in reports.items():
 verify(r)
 assert not r.get('candidate_sha256')or r['candidate_sha256']==ch
 if state[k]['direct_captured_loader']:
  loads=[x for row in r['suites'].values()for item in row for x in item['loader']]
 else:loads=read(P/('raw-'+k+'.loader.json'))['loads']
 hs={x['elf_sha256']for x in loads};assert ch in hs and original in hs,k
ad=audit(reports);assert not ad['mismatches'];(P/'FINAL-DIAGNOSTICS.json').write_text(json.dumps(ad,indent=2)+'\n')
helper=read(P/'raw-authority-match.json')['candidates'][0];callee=read(P/'callee-match.json')['candidates'][0];assert helper['bytes']==2080 and helper['normalized_equal'];assert callee['bytes']==2192 and callee['normalized_equal']
files=['trade_v3.rs','sell_v2.rs','v2_user_token_transfers.rs'];source_hashes={f:sha(src/'src'/f)for f in files}
for f in files:assert source_hashes[f]==sha(b/'source/programs/pump/src'/f)
changed=[str(f.relative_to(src))for f in src.rglob('*')if f.is_file()and(not(base/f.relative_to(src)).exists()or f.read_bytes()!=(base/f.relative_to(src)).read_bytes())];assert sorted(changed)==sorted('src/'+f for f in files),changed
patch=''
for f in files:
 old=(base/'src'/f).read_text().splitlines(True)if(base/'src'/f).exists()else[]
 patch+=''.join(difflib.unified_diff(old,(src/'src'/f).read_text().splitlines(True),fromfile='a/src/'+f,tofile='b/src/'+f))
(P/'shared-sell-transfer.patch').write_text(patch)
r={'scope':'Verified original shared SellV2/SellV3 user-token transfer helper with real two-caller reuse.','base':str(base),'source':str(src),'source_sha256':source_hashes,'candidate_sha256':ch,'unstripped_sha256':sha(b/'unstripped.so'),'original_sha256':original,'signed_cases':sum(counts.values()),'case_counts':counts,'mismatches':[],'diagnostic_mismatches':0,'helper_original_start':'0x8fe18','helper_bytes':2080,'helper_normalized_equal':True,'helper_raw_equal':False,'direct_callee':{'original_start':'0x17fcc8','candidate_start':hex(callee['start']),'bytes':2192,'normalized_equal':True,'name':'anchor_spl::token_2022::transfer_checked'},'normalized_windows':706,'raw_windows':120,'inventory_delta_vs_round20':read(P/'RAW-INVENTORY-DELTA.json'),'abi_evidence':['Original caller0x1460c0 passes Signer.info as a raw AccountInfo pointer, and helper0x90128 reads itsRc fields directly.','Both real original callsites0x1460e0 and0x14b260 now delegate to the shared Rust helper.','Function pointer levels, clone order, nozero guard, empty signer-seed path and success/error ABI match original instructions.'],'visibility_control':'Corrected-authority pub(crate) control stays2048B/253slots; publicly reachable module/function preserves original typed ABI and reaches2080B/0slots. Exact original source visibility is not independently known; no dummy callers or no_mangle were used.','patch':'shared-sell-transfer.patch','integration':'Apply the three-file patch together; fee-wrapper and net-budget controls are excluded. All source snapshots and imported context helper versions remain frozen.'}
(P/'FINAL-RESULT.json').write_text(json.dumps(r,indent=2)+'\n')
priv=read(P/'raw-private-match.json')['candidates'][0];pr={'source':'raw-private-source','helper_sha256':sha(P/'raw-private-source/src/v2_user_token_transfers.rs'),'candidate_sha256':sha(P/'raw-private-build/candidate.so'),'unstripped_sha256':sha(P/'raw-private-build/unstripped.so'),'bytes':priv['bytes'],'different_slots':len(priv['different_slots']),'status':'Negative visibility control; no new exact body. Runtime not rerun because not proposed for promotion.'};(P/'RAW-PRIVATE-RESULT.json').write_text(json.dumps(pr,indent=2)+'\n')
for d in [b,P/'raw-private-build']:
 t=d/'target';assert t.is_dir()and not t.is_symlink();rec={'candidate_sha256':sha(d/'candidate.so'),'unstripped_sha256':sha(d/'unstripped.so'),'reason':'Completed validated/negative control target; all source, logs, receipts and ELF outputs retained.'};shutil.rmtree(t);(d/'RETIRED-TARGET.json').write_text(json.dumps(rec,indent=2)+'\n')
(P/'LIVE-STATE.json').write_text(json.dumps({'status':'Complete','pending_jobs':[],'final_report':'FINAL-RESULT.json'},indent=2)+'\n')
allfiles=[f for f in P.rglob('*')if f.is_file()and f.name!='EVIDENCE-MANIFEST.json'];(P/'EVIDENCE-MANIFEST.json').write_text(json.dumps({'files':{str(f.relative_to(P)):sha(f)for f in sorted(allfiles)}},indent=2)+'\n');print(json.dumps(r,indent=2))
