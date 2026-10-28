from pathlib import Path
import json,gzip,hashlib,sys
sys.path.insert(0,'scripts')
from pump_diagnostic_audit import audit
P=Path('work/parallel-main-v3-validity')
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
state=read(P/'byte-regression-state.json');assert len(state)==15
assert all(x['returncode']==0 for x in state.values())
reports={k:read(Path(v['output']))for k,v in state.items()};reports['flags']=read(P/'byte-flags-after.json.gz')
counts={k:v['case_count']for k,v in reports.items()};assert sum(counts.values())==866
for k,v in reports.items():
 assert not v.get('mismatches'),k
 assert all(not r.get('mismatches')for r in v['cases']),k
 if 'candidate_sha256'in v:assert v['candidate_sha256']==sh(P/'byte-build/candidate.so'),k
 loader=read(P/('byte-'+k+'.loader.json')) if k!='flags' else read(P/'byte-flags-after.loader.json')
 loaded={x['elf_sha256']for x in loader['loads']};assert sh(P/'byte-build/candidate.so')in loaded,k
 assert '7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d'in loaded,k
 if 'passed'in v:assert v['passed']==v['case_count'],k
ad=audit(reports);assert not ad['mismatches'];(P/'BYTE-DIAGNOSTICS.json').write_text(json.dumps(ad,indent=2)+'\n')
inv=read(P/'byte-build/local-body-inventory.json');old=read(P/'build/local-body-inventory.json')
def ids(a,key):return {x['start']for x in a['windows']if x[key]}
delta={k:{'gains':sorted(ids(inv,k)-ids(old,k)),'losses':sorted(ids(old,k)-ids(inv,k))}for k in ['normalized_matches','raw_matches']}
assert not any(d['gains']or d['losses']for d in delta.values())
match=read(P/'byte-helper-match.json')['candidates'][0]
res={'scope':'Verified u8 representation of original trade-validity input flags, retaining real four-caller extraction and MultiHop cashback correction.','source':'work/parallel-main-v3-validity/byte-source','source_sha256':{f:sh(P/'byte-source/src'/f)for f in ['trade_v3.rs','multi_hop_curve.rs']},'candidate_sha256':sh(P/'byte-build/candidate.so'),'unstripped_sha256':sh(P/'byte-build/unstripped.so'),'signed_cases':sum(counts.values()),'case_counts':counts,'mismatches':[],'diagnostic_mismatches':len(ad['mismatches']),'original_helper_bytes':992,'candidate_helper_bytes':match['bytes'],'helper_normalized_differing_slots':len(match['different_slots']),'remaining_differences':'Three branch/input-mask scheduling slots and two real source-line metadata slots. No coordinate padding.','normalized_windows':inv['normalized_equal_windows'],'raw_windows':inv['raw_equal_windows'],'inventory_delta_vs_verified_bool_source':delta,'integration':'Copy only the two owned source files. Preserve context-owned agreed checked_ceil_div dependency; do not replace fee_cpi.rs wholesale.','supersedes_only':'The bool-parameter pair in RESULT.json. That semantic baseline remains frozen.'}
(P/'BYTE-RESULT.json').write_text(json.dumps(res,indent=2)+'\n')
for fname in ['trade_v3.rs','multi_hop_curve.rs']:
 assert sh(P/'byte-source/src'/fname)==sh(P/'byte-build/source/programs/pump/src'/fname)
print(json.dumps(res,indent=2))
