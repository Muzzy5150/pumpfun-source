"""Focused signed legacy-Sell regression: existing base and fee-override cases."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,re,sys
from solders.transaction import VersionedTransaction
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'scripts'),str(R/'work/parallel-main-loader-optimized')]
import pump_captured_loader as loader
loader.install()
import pump_legacy_sell_differential as h
import pump_legacy_sell_configured_fee_differential as c
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for group,cases in [('legacy_sell',h.cases()),('configured_fee',c.cases())]:
 for case in cases:
  start=len(loader.LOADS);o=h.run(case);n=h.run(case,a.candidate);loads=loader.LOADS[start:];assert len(loads)==2
  for result in [o,n]:assert all(VersionedTransaction.from_bytes(base64.b64decode(result['transaction_base64'])).verify_with_results())
  assert o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','before','accounts','events','inner','return_data']if o[k]!=n[k]];rows.append({'suite':group,'case':case,'original':o,'candidate':n,'different_fields':diff,'loader':loads})
  if diff:print(json.dumps({'case':case,'different_fields':diff}),flush=True)
diag=audit({'legacy_sell':rows});out={'case_count':len(rows),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'suites':{'legacy_sell':rows},'diagnostics':diag,'mismatches':[i for i,x in enumerate(rows)if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(out).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(out['mismatches']),'strict':len(diag['mismatches'])}),flush=True)
