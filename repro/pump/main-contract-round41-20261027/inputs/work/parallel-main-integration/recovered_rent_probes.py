"""Serial replay of recovered V2 creator-rent cases under the outer captured loader."""
from pathlib import Path
import argparse,base64,gzip,hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'work/parallel-main-v2-helpers')]
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
path=ROOT/'work/parallel-main-v2-helpers/rent-probe.py';spec=importlib.util.spec_from_file_location('recovered_creator_rent',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=[]
for c in m.cases():
 row=m.execute((c,str(a.candidate.resolve())));rows.append(row)
 for result in [row['original'],row['candidate']]:assert all(VersionedTransaction.from_bytes(base64.b64decode(result['transaction_base64'])).verify_with_results())
 if row['different_fields']:print('MISMATCH',c['name'],row['different_fields'],flush=True)
d=audit({'creator_rent':rows});r={'scope':__doc__,'case_count':len(rows),'candidate_sha256':sha(a.candidate),'input_sha256':{str(path):sha(path),str(Path(__file__)):sha(__file__)},'cases':rows,'mismatches':[i for i,row in enumerate(rows)if row['different_fields']],'diagnostics':d};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print({'cases':len(rows),'mismatches':r['mismatches'],'strict_mismatches':len(d['mismatches'])});assert not r['mismatches']and not d['mismatches']
