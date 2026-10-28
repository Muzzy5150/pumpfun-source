from pathlib import Path
import json,hashlib,shutil
P=Path('work/parallel-main-v3-validity')
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
base=read(P/'byte-build/local-body-inventory.json');trial=read(P/'predicate-build/local-body-inventory.json')
def ids(a,k):return {x['start']for x in a['windows']if x[k]}
delta={k:{'gains':sorted(ids(trial,k)-ids(base,k)),'losses':sorted(ids(base,k)-ids(trial,k))}for k in ['raw_matches','normalized_matches']}
match=read(P/'predicate-helper-match.json')['candidates'][0]
result={'scope':'Single evidence-led natural OR require control of trade-validity helper; negative result, no promotion.','source':'work/parallel-main-v3-validity/predicate-source','source_sha256':{f:sh(P/'predicate-source/src'/f)for f in ['trade_v3.rs','multi_hop_curve.rs']},'candidate_sha256':sh(P/'predicate-build/candidate.so'),'unstripped_sha256':sh(P/'predicate-build/unstripped.so'),'candidate_helper_bytes':match['bytes'],'helper_normalized_differing_slots':len(match['different_slots']),'inventory_delta_vs_verified_byte_source':delta,'normalized_windows':trial['normalized_equal_windows'],'raw_windows':trial['raw_equal_windows'],'result':'Same five differing normalized instruction slots as byte source; no new exact body. No runtime suite was repeated because this control is not proposed for promotion.','source_coordinate_policy':'Actual source line constants retained; no padding or artificial coordinates.'}
(P/'PREDICATE-RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
for name in ['byte','predicate']:
 build=P/(name+'-build'); rec={'reason':'Completed control target retirement after retained ELF hash verification.','candidate_sha256':sh(build/'candidate.so'),'unstripped_sha256':sh(build/'unstripped.so'),'target':str(build/'target')}
 if name=='byte':
  old=read(P/'BYTE-RESULT.json');assert old['candidate_sha256']==rec['candidate_sha256'];assert old['unstripped_sha256']==rec['unstripped_sha256']
 target=build/'target';assert target.is_dir()and not target.is_symlink()
 shutil.rmtree(target)
 (build/'RETIRED-TARGET.json').write_text(json.dumps(rec,indent=2)+'\n')
 assert rec['candidate_sha256']==sh(build/'candidate.so')and rec['unstripped_sha256']==sh(build/'unstripped.so')
# Dedicated new manifest leaves earlier frozen manifest untouched.
files=[p for p in P.rglob('*')if p.is_file()and (p.name.startswith('byte-')or p.name in ['BYTE-RESULT.json','BYTE-DIAGNOSTICS.json','PREDICATE-RESULT.json','BYTE-CONTROL.json','PREDICATE-CONTROL.json'])]
for d in ['byte-source','predicate-source','byte-build','predicate-build']:
 files.extend(p for p in (P/d).rglob('*')if p.is_file())
files=sorted(set(files))
(P/'BYTE-PREDICATE-MANIFEST.json').write_text(json.dumps({'files':{str(p.relative_to(P)):sh(p)for p in files}},indent=2)+'\n')
print(json.dumps({'predicate':result,'manifest_files':len(files)},indent=2))
