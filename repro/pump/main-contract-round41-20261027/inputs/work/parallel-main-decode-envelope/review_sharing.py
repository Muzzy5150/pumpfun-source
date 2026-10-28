from pathlib import Path
import base64,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reports={name:json.loads((W/(name+'-full.json')).read_bytes())for name in ['distribution','minimum']}
diag=audit(reports);assert not diag['mismatches'];(W/'sharing-full-diagnostics.json').write_text(json.dumps(diag,indent=2)+'\n')
probe=json.loads((W/'sharing-probe.json').read_bytes());assert probe['passed']and probe['case_count']==78
transactions=set()
def walk(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k=='transaction_base64'and isinstance(v,str):transactions.add(v)
   else:walk(v)
 elif isinstance(x,list):
  for y in x:walk(y)
for report in [*reports.values(),probe]:walk(report)
for value in transactions:assert all(VersionedTransaction.from_bytes(base64.b64decode(value)).verify_with_results())
build=W/'build-sharing-config';b=json.loads((build/'build-comparison.json').read_bytes());assert b['returncode']==0 and b['source_unchanged'];assert sha(build/'candidate.so')==b['comparison']['candidate_sha256']and sha(build/'unstripped.so')==b['unstripped_sha256']
base=json.loads((ROOT/'work/parallel-main-integration/build-round14/normalized-inventory.json').read_bytes());new=json.loads((build/'normalized-inventory.json').read_bytes());ss=lambda r:{w['start']for w in r['windows']if w['normalized_matches']};before=ss(base);after=ss(new);assert after-before=={0x116158}and not before-after
for addr in [0x9b6a0,0x9bc28,0x9c240,0x9c8f8,0x9d008,0x9d850,0x9e178,0x9eaf0,0x9f500]:assert addr in after
loaders={}
for name in ['sharing-probe','distribution-full','minimum-full']:
 p=W/(name+'.loader.json');r=json.loads(p.read_bytes());assert r['loads']
 for row in r['loads']:
  assert row['elf_sha256']in[b['comparison']['candidate_sha256'],'7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d']
  assert row['program_owner']=='BPFLoaderUpgradeab1e11111111111111111111111'and row['program_bytes']==36 and row['programdata_bytes']==10485760 and row['elf_prefix_unchanged']and row['zero_allocation_tail']
 loaders[name]={'sha256':sha(p),'loads':len(r['loads'])}
counts={n:len(r['cases'])for n,r in reports.items()};assert counts=={'distribution':298,'minimum':181}
source=W/'source-sharing-config/src/distribution.rs';plan=json.loads((W/'sharing-config-plan.json').read_bytes());assert sha(source)==plan['distribution_sha256']
result={'status':'passed','scope':'Only SharingConfig AccountDeserialize in main Pump. Restore standard generated Anchor error conversions; exact unchecked decoder added, no handler/owner/field change. Not complete ELF identity.','baseline_source':plan['baseline'],'base_distribution_sha256':plan['base_distribution_sha256'],'source':str(source),'source_sha256':sha(source),'patch':str(W/'sharing-config-from-round14.patch'),'patch_sha256':sha(W/'sharing-config-from-round14.patch'),'candidate_sha256':b['comparison']['candidate_sha256'],'unstripped_sha256':b['unstripped_sha256'],'build_receipt_sha256':sha(build/'build-comparison.json'),'baseline_counts':base['counts'],'counts':new['counts'],'baseline_normalized_windows':sorted(before),'candidate_normalized_windows':sorted(after),'gains':[hex(x)for x in sorted(after-before)],'losses':[hex(x)for x in sorted(before-after)],'all_nine_curve_leaves_preserved':True,'signed_cases':{'focused':78,**counts},'full_diagnostics':diag,'focused_diagnostics':probe['diagnostics'],'distinct_transactions_reverified':len(transactions),'loaders':loaders,'checked_residual':'744 B matches original size; only ErrorOrigin line84 vs17 and source path length24 vs33 remain. Original source path is programs/pump/src/lib.rs. No coordinate edits proposed.','unchecked_body':'Original0x116158/1472B exactly normalized; zero differing slots.'}
(W/'SHARING-CONFIG-REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['status','candidate_sha256','counts','gains','losses','signed_cases','distinct_transactions_reverified']}));print('diagnostics',diag['log_bearing_cases'])
