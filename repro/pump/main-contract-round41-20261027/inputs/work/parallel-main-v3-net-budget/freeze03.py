from pathlib import Path
import json,gzip,hashlib,difflib,shutil,sys
sys.path.insert(0,'scripts');from pump_diagnostic_audit import audit
P=Path('work/parallel-main-v3-net-budget');base=Path('work/parallel-main-integration/round17-source/programs/pump')
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
state=read(P/'regression03-state.json');assert len(state)==15;assert all(v['returncode']==0 for v in state.values())
reports={k:read(Path(v['output']))for k,v in state.items()};reports['budget96']=read(P/'after03.json.gz');counts={k:v['case_count']for k,v in reports.items()};assert sum(counts.values())==946
for k,v in reports.items():
 assert not v.get('mismatches'),k
 assert all(not r.get('mismatches')and not r.get('different_fields')and r.get('match')is not False for r in v['cases']),k
 loader=read(P/('after03.loader.json'if k=='budget96'else'03-'+k+'.loader.json'))
 loaded={r['elf_sha256']for r in loader['loads']};assert sh(P/'build03/candidate.so')in loaded,k
 assert '7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d'in loaded,k
 assert not v.get('candidate_sha256')or v['candidate_sha256']==sh(P/'build03/candidate.so')
assert not audit(reports)['mismatches']
assert sh(P/'source03/src/trade_v3.rs')==sh(P/'build03/source/programs/pump/src/trade_v3.rs')
changes=[str(p.relative_to(P/'source03'))for p in (P/'source03').rglob('*')if p.is_file()and p.read_bytes()!=(base/p.relative_to(P/'source03')).read_bytes()];assert changes==['src/trade_v3.rs'],changes
inv=read(P/'build03/local-body-inventory.json');orig=read(Path('work/parallel-main-integration/build-round17/normalized-inventory.json'))
n_old={r['start']for r in orig['windows']if r['normalized_matches']};n_new={r['start']for r in inv['windows']if r['normalized_matches']};r_old={r['start']for r in orig['windows']if r['raw_match']};r_new={r['start']for r in inv['windows']if r['raw_matches']}
delta={'normalized':{'gains':sorted(n_new-n_old),'losses':sorted(n_old-n_new)},'raw':{'gains':sorted(r_new-r_old),'losses':sorted(r_old-r_new)}}
match=read(P/'helper-match03.json')['candidates'][0]
result={'scope':'Verified structural reconstruction of original five-u64 V3 net-budget helper; no new observed semantic gap in focused96 or regression850.','base':str(base),'source':str(P/'source03'),'source_sha256':sh(P/'source03/src/trade_v3.rs'),'owned_changes':changes,'candidate_sha256':sh(P/'build03/candidate.so'),'unstripped_sha256':sh(P/'build03/unstripped.so'),'original_sha256':'7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d','case_counts':counts,'signed_cases':sum(counts.values()),'mismatches':[],'diagnostic_mismatches':0,'original_helper_bytes':1840,'candidate_helper_bytes':match['bytes'],'helper_normalized_differing_slots':len(match['different_slots']),'normalized_windows':inv['normalized_equal_windows'],'raw_windows':inv['raw_equal_windows'],'inventory_delta_vs_round17':delta,'structural_recovery':['Result<(quote,protocol_amount,creator_amount,protocol_bps,original_creator_bps)> with amounts calculated before quote correction.','Effective creator fee becomes0 for zero creator; returned original creator bps preserved.','Checked total bps, saturating aggregate excess correction, require_gt quote gates and compared operands.','Two genuine V3 calls use existing shared fee API; post-completion call is guarded by original nominal>=2 policy.'],'limitations':['Original helper remains40 bytes smaller;203 positional normalized differences.','No new normalized exact body. Seven additional raw-equal bodies arise within existing normalized matches and should not be treated as recovered new functions.','Original third direct caller in MultiHop is mapped read-only and remains outside this proposed trade_v3-only increment.','Shared fee helper remains owned by context lane; no fee_cpi.rs changes.'],'integration':'Optional structural proposal: copy only source03/src/trade_v3.rs onto Round17 or newer compatible source, rerun combined verification. Both earlier tuple controls remain frozen negative evidence.'}
(P/'RESULT03.json').write_text(json.dumps(result,indent=2)+'\n')
patch=''.join(difflib.unified_diff((base/'src/trade_v3.rs').read_text().splitlines(True),(P/'source03/src/trade_v3.rs').read_text().splitlines(True),fromfile='a/src/trade_v3.rs',tofile='b/src/trade_v3.rs'));(P/'net-budget-from-round17.patch').write_text(patch)
for name in ['build02','build03']:
 b=P/name;t=b/'target';rec={'reason':'Completed control target retirement; retained both exact ELF outputs and source/build receipts.','candidate_sha256':sh(b/'candidate.so'),'unstripped_sha256':sh(b/'unstripped.so'),'target':str(t)}
 assert t.is_dir()and not t.is_symlink();shutil.rmtree(t);(b/'RETIRED-TARGET.json').write_text(json.dumps(rec,indent=2)+'\n');assert sh(b/'candidate.so')==rec['candidate_sha256'];assert sh(b/'unstripped.so')==rec['unstripped_sha256']
files=[p for p in P.rglob('*')if p.is_file()and p.name!='EVIDENCE-MANIFEST03.json'];(P/'EVIDENCE-MANIFEST03.json').write_text(json.dumps({'files':{str(p.relative_to(P)):sh(p)for p in sorted(files)}},indent=2)+'\n')
print(json.dumps(result,indent=2))
