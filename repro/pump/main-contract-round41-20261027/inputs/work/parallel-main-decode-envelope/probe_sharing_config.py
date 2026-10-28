"""Focused signed SharingConfig parser boundaries, using unchanged distribution fixtures."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import pump_creator_distribution_differential as distribution
import pump_minimum_fee_differential as minimum
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction
import base64
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
inputs={str(x):sha(x)for x in [Path(__file__),Path(distribution.__file__),Path(minimum.__file__),a.candidate,ROOT/'evidence/original/pump/deployed.so']}
reports={};signed=set()
for name,module,cases in [
 ('distribution',distribution,[c for c in distribution.cases()if any(key in c['name']for key in ['sharing-','status-','version-','-base','two-rounding','duplicate-old','empty-old'])]),
 ('minimum',minimum,[c for c in minimum.cases()if ('sharing' in c.get('patch',{}))or 'version'in c or 'status'in c or 'revoked'in c or c==minimum.cases()[0]])]:
 rows=[]
 for c in cases:
  o=module.run(c);n=module.run(c,a.candidate)
  if name=='distribution':fields=['error','before','after','events','inner','return'];diff=[k for k in fields if o[k]!=n[k]]
  else:
   diff=[k for k in ['error','before','after','events']if o[k]!=n[k]]
   diff += [k for k in ['return_data','inner_instructions']if o['metadata'][k]!=n['metadata'][k]]
  for x in [o,n]:
   tx=x['transaction_base64'];assert all(VersionedTransaction.from_bytes(base64.b64decode(tx)).verify_with_results());signed.add(tx)
  rows.append({'case':c,'original':o,'candidate':n,'differences':diff})
 reports[name]={'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['differences']]}
assert inputs=={path:sha(Path(path))for path in inputs}
diag=audit(reports)
result={'scope':__doc__,'input_sha256':inputs,'suites':reports,'case_count':sum(r['case_count']for r in reports.values()),'diagnostics':diag,'distinct_signed_transactions':len(signed),'passed':not diag['mismatches']and not any(r['mismatches']for r in reports.values())}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['case_count','distinct_signed_transactions','passed']}));assert result['passed']
