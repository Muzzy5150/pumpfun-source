from pathlib import Path
import sys,json,gzip,hashlib,difflib
P=Path(__file__).resolve().parent;R=P.parents[1];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(P))
from pump_diagnostic_audit import audit
from audit_invocations import audit_invocations
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
state=json.loads((P/'regression-state.json').read_text());retries=json.loads((P/'retry-state02.json').read_text());suites={};reports={};counts={}
for name,row in state.items():
 if row['returncode']!=0:
  row=retries[name];assert row['returncode']==0
 path=Path(row['output']);raw=path.read_bytes();d=json.loads(gzip.decompress(raw)if raw[:2]==b'\x1f\x8b'else raw)
 assert not d.get('mismatches'),(name,d.get('mismatches'))
 assert not d.get('diagnostics',{}).get('mismatches'),name
 suites[name]=d;reports[name]={'path':str(path),'sha256':sha(path)}
 counts[name]=d.get('case_count',len(d.get('cases',[])))
 assert counts[name]>0,(name,d.keys())
diag=audit(suites);assert not diag['mismatches'],diag
(P/'diagnostic-audit02.json').write_text(json.dumps(diag,indent=2)+'\n')
inv={k:audit_invocations(v)for k,v in suites.items()};(P/'invocation-audit-all02.json').write_text(json.dumps(inv,indent=2)+'\n')
assert not any(v['mismatches']for k,v in inv.items()if k.startswith('buyback'))
base=R/'work/parallel-main-integration/round21-source/programs/pump';source=P/'source02';changed=[]
for path in source.rglob('*'):
 if path.is_file() and path.relative_to(source).parts[0] not in ('target',):
  other=base/path.relative_to(source)
  if not other.exists() or sha(path)!=sha(other):changed.append(str(path.relative_to(source)))
assert changed==['src/trade_v3.rs'],changed
old=(base/'src/trade_v3.rs').read_text();new=(source/'src/trade_v3.rs').read_text();(P/'v3-buyback-assert02.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/src/trade_v3.rs',tofile='b/src/trade_v3.rs')))
a=json.loads((R/'work/parallel-main-integration/build-round21/normalized-inventory.json').read_text());b=json.loads((P/'build02/local-body-inventory.json').read_text())
def keys(d,k):return {x['start']for x in d['windows']if x.get(k,x.get('raw_match')if k=='raw_matches'else None)}
delta={k:{'gains':sorted(keys(b,k)-keys(a,k)),'losses':sorted(keys(a,k)-keys(b,k))}for k in ['raw_matches','normalized_matches']}
result={'scope':'V3 buyback panic behavior and original payment/error ordering; isolated semantic correction.','base':str(base),'source':str(source),'changed_files':changed,'source_sha256':sha(source/'src/trade_v3.rs'),'candidate_sha256':sha(P/'build02/candidate.so'),'unstripped_sha256':sha(P/'build02/unstripped.so'),'original_sha256':sha(R/'evidence/original/pump/deployed.so'),'signed_cases':sum(counts.values()),'case_counts':counts,'diagnostic_log_bearing_cases':diag['log_bearing_cases'],'mismatches':[],'diagnostic_mismatches':len(diag['mismatches']),'focused_cpi_invocation_mismatches':0,'all_cpi_invocation_audit':{k:{'paired_cases':v['paired_cases'],'mismatches':len(v['mismatches'])}for k,v in inv.items()},'normalized_windows':b['normalized_equal_windows'],'raw_windows':b['raw_equal_windows'],'inventory_delta_vs_round21':delta,'before_evidence':'PAYMENT-ORDER-PROOF.json','counterexamples_fixed':{'different_fields_cases':32,'invocation_order_cases':8,'note':'Invocation and field counts overlap; 89 focused cases in total.'},'original_boundary':'0x80df8/2120B: quotient conversion then checked remainder for initial protocol fee before post-completion protocol fee. Distinct V3 accounting boundary retained as future body-recovery target.','behavior':['Preserve exact quotient conversion and remainder panic messages.','Buy/exact accounting follows pool/pricing checks and precedes limits.','Sell base/user transfers precede buyback assertion; protocol accrual follows user payout and precedes buyback payout.','Separate native user and buyback debits retain their distinct arithmetic failure order.'],'limitations':['No normalized or raw window gain; whole ELF remains unequal.','Source coordinates and compute use are not compared in diagnostic audit.','Three interrupted jobs had system ENFILE/import errors; successful fresh-output sequential retries used unchanged ELF/source and are preserved beside initial attempts.'],'patch':'v3-buyback-assert02.patch','build_receipt':'build02/build-comparison.json','reports':reports}
assert result['signed_cases']==1234,result['signed_cases']
(P/'FINAL-RESULT02.json').write_text(json.dumps(result,indent=2)+'\n')
files=[x for x in P.rglob('*')if x.is_file()and 'target'not in x.parts and 'cargo-home'not in x.parts and 'source'in x.parts and False]
selected=[source/'src/trade_v3.rs',P/'build02/candidate.so',P/'build02/unstripped.so',P/'build02/build-comparison.json',P/'build02/build-attempt.json',P/'build02/local-body-inventory.json',P/'FINAL-RESULT02.json',P/'diagnostic-audit02.json',P/'invocation-audit-all02.json',P/'v3-buyback-assert02.patch',P/'PAYMENT-ORDER-PROOF.json',P/'PROOF-BEFORE.json',P/'regression-state.json',P/'retry-state02.json',P/'audit_invocations.py']+[Path(v['path'])for v in reports.values()]+list(P.glob('probe*.py'))
manifest={str(x.relative_to(P)):sha(x)for x in selected};(P/'EVIDENCE-MANIFEST02.json').write_text(json.dumps(manifest,indent=2)+'\n')
(P/'LIVE-STATE.json').write_text(json.dumps({'state':'validation complete','source':'source02','build':'build02','signed_cases':1234,'result':'FINAL-RESULT02.json','manifest':'EVIDENCE-MANIFEST02.json','active_jobs':[]},indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k not in ('reports','all_cpi_invocation_audit')},indent=2))
