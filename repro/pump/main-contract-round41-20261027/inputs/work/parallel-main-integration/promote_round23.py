"""Promote only source proven by the completed Round23 build and signed corpus."""
from pathlib import Path
import gzip,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from build_source_manifest import source_manifest
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();base=W/'round22-source/programs/pump';new=W/'round23-final-source/programs/pump';canonical=ROOT/'programs/pump'
def relative_map(mapping,directory):
 return {(Path(k)if Path(k).is_absolute() else ROOT/k).relative_to(directory):v for k,v in mapping.items()}
old_record=json.loads((W/'build-round22/build-comparison.json').read_text());record=json.loads((W/'build-round23-final/build-comparison.json').read_text());old=relative_map(old_record.get('primary_source_sha256',old_record['source_sha256']),base);desired=relative_map(record['primary_source_sha256'],new)
full=json.loads(gzip.decompress((W/'round23-captured-full.json.gz').read_bytes()));extra=json.loads(gzip.decompress((W/'round23-captured-additional.json.gz').read_bytes()));parity=json.loads((W/'round23-cached-repeat-parity.json').read_text())
assert full['case_count']==10468 and len(full['suites'])==44 and not full['diagnostics']['mismatches'];assert extra['case_count']==5792 and extra['suite_count']==116 and not extra['diagnostics']['mismatches'];assert full['candidate_sha256']==extra['candidate_sha256']==record['comparison']['candidate_sha256'];assert all(v['cached']==v['repeat']for v in parity.values())
actual=relative_map(source_manifest(canonical,canonical,ROOT),canonical);assert actual==old,'canonical main source changed since verified Round22';assert all(sha(new/p)==v for p,v in desired.items()),'validated Round23 primary changed'
pre={'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'origin_main':subprocess.check_output(['git','rev-parse','origin/main'],text=True).strip(),'source_sha256':{str(p):v for p,v in old.items()}};(W/'canonical-pre-round23.json').write_text(json.dumps(pre,indent=2)+'\n')
for p in old.keys()-desired.keys():(canonical/p).unlink()
for p in desired:
 target=canonical/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((new/p).read_bytes())
assert relative_map(source_manifest(canonical,canonical,ROOT),canonical)==desired
out={'scope':__doc__,'files':len(desired),'removed':[str(p)for p in old.keys()-desired.keys()],'added':[str(p)for p in desired.keys()-old.keys()],'candidate_sha256':full['candidate_sha256'],'unstripped_sha256':record['unstripped_sha256'],'source_sha256':{str(p):v for p,v in desired.items()},'full_cases':10468,'additional_cases':5792,'strict_log_cases':full['diagnostics']['log_bearing_cases']+extra['diagnostics']['log_bearing_cases'],'whole_elf_equal':False,'goal_complete':False,'legacy_receipt_schema_fallback':not bool(old_record.get('primary_source_sha256')),'reports_sha256':{p.name:sha(p)for p in [W/'round23-captured-full.json.gz',W/'round23-captured-additional.json.gz',W/'round23-cached-repeat-parity.json']}}
(W/'round23-promotion.json').write_text(json.dumps(out,indent=2)+'\n');print({k:out[k]for k in ['files','removed','added','candidate_sha256','strict_log_cases']},flush=True)
