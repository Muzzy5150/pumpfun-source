from pathlib import Path
import gzip,json,hashlib,sys,shutil
sys.path.insert(0,'scripts');from pump_diagnostic_audit import audit
P=Path(__file__).parent
sh=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
s=read(P/'regression-state.json');assert len(s)==15 and all(v['returncode']==0 for v in s.values());reports={k:read(Path(v['output']))for k,v in s.items()};reports['sell-supply16']=read(P/'focused-after.json.gz');reports['zero-reserve4']=read(P/'zero-after.json.gz');counts={k:v['case_count']for k,v in reports.items()};assert sum(counts.values())==870
for k,v in reports.items():
 assert not v.get('mismatches'),k
 assert all(not row.get('different_fields')and not row.get('mismatches')and row.get('match')is not False for row in v['cases']),k
 if 'passed'in v:assert v['passed']==v['case_count']
 loader=read(P/('focused-after.loader.json'if k=='sell-supply16'else'zero-after.loader.json'if k=='zero-reserve4'else k+'.loader.json'))
 hashes={r['elf_sha256']for r in loader['loads']};assert sh(P/'build/candidate.so')in hashes and '7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d'in hashes,k
ad=audit(reports);assert not ad['mismatches'];(P/'DIAGNOSTICS-FULL.json').write_text(json.dumps(ad,indent=2)+'\n')
base=Path('work/parallel-main-integration/round18-source/programs/pump');changed=[str(p.relative_to(P/'source'))for p in (P/'source').rglob('*')if p.is_file()and p.read_bytes()!=(base/p.relative_to(P/'source')).read_bytes()];assert changed==['src/trade_v3.rs']
assert sh(P/'source/src/trade_v3.rs')==sh(P/'build/source/programs/pump/src/trade_v3.rs')
old=read(Path('work/parallel-main-integration/build-round18/normalized-inventory.json'));new=read(P/'build/local-body-inventory.json')
sets=lambda doc,key:{r['start']for r in doc['windows']if r[key]}
delta={'normalized':{'gains':sorted(sets(new,'normalized_matches')-sets(old,'normalized_matches')),'losses':sorted(sets(old,'normalized_matches')-sets(new,'normalized_matches'))},'raw':{'gains':sorted(sets(new,'raw_matches')-sets(old,'raw_match')),'losses':sorted(sets(old,'raw_match')-sets(new,'raw_matches'))}}
r={'scope':'Verified minimal V3 sell fee-market-cap correction from frozen Round18; no optional tuple control included.','base':str(base),'owned_changes':changed,'source':str(P/'source/src/trade_v3.rs'),'source_sha256':sh(P/'source/src/trade_v3.rs'),'candidate_sha256':sh(P/'build/candidate.so'),'unstripped_sha256':sh(P/'build/unstripped.so'),'original_sha256':'7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d','signed_cases':870,'case_counts':counts,'mismatches':[],'diagnostic_mismatches':0,'fixed_counterexamples':{'fee_tier_selection':4,'zero_reserve_error':2},'normalized_windows':new['normalized_equal_windows'],'raw_windows':new['raw_equal_windows'],'inventory_delta_vs_round18':delta,'behavior':'Ordinary sells use mint.supply for fee-market cap; mayhem uses stored curve supply. Zero virtual token reserve returns DivisionByZero6026 after existing zero-input gate6022.','patch':'sell-supply.patch','new_probe_cases':20,'integration':'Copy only source/src/trade_v3.rs; new probes and all source snapshots are frozen.'}
(P/'FULL-RESULT.json').write_text(json.dumps(r,indent=2)+'\n')
t=P/'build/target';assert t.is_dir()and not t.is_symlink();shutil.rmtree(t);(P/'build/RETIRED-TARGET.json').write_text(json.dumps({'reason':'All870 signed cases and diagnostics passed; source, ELF outputs and receipts retained.','candidate_sha256':r['candidate_sha256'],'unstripped_sha256':r['unstripped_sha256']},indent=2)+'\n')
files=[f for f in P.rglob('*')if f.is_file()and f.name!='EVIDENCE-MANIFEST.json'];(P/'EVIDENCE-MANIFEST.json').write_text(json.dumps({'files':{str(f.relative_to(P)):sh(f)for f in sorted(files)}},indent=2)+'\n');print(json.dumps(r,indent=2))
