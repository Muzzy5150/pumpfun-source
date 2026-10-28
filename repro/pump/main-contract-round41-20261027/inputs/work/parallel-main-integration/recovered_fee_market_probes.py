"""Serial execution of the frozen fee-market-cap counterexamples under the outer loader."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();path=R/'work/parallel-main-fee-market-cap/probe-boundaries.py'
spec=importlib.util.spec_from_file_location('frozen_fee_market_cases',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);rows=[]
for module,case in m.cases():
 row=m.execute((module,case,str(a.candidate.resolve())));rows.append(row)
 if row['different_fields']:print('MISMATCH',case['name'],row['different_fields'],flush=True)
d=audit({'market_cap':rows});sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r={'scope':__doc__,'case_count':len(rows),'candidate_sha256':sha(a.candidate),'original_sha256':sha(R/'evidence/original/pump/deployed.so'),'input_sha256':{str(path):sha(path),str(Path(__file__)):sha(__file__)},'cases':rows,'diagnostics':d,'mismatches':[i for i,row in enumerate(rows)if row['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print({'case_count':len(rows),'mismatches':r['mismatches'],'strict_mismatches':len(d['mismatches'])});assert not r['mismatches']and not d['mismatches']
