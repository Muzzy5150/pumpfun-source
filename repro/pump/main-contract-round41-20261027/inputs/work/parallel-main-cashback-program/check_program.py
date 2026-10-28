"""Signed Cashback self-program validation edges."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import pump_cashback_differential as fixture
parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
rows=[]
for mode in [{},{'v2':True},{'v2':True,'token_quote':True}]:
    for zero in [False,True]:
        case={**mode,'wrong_keys':['program'],'lamports':100 if zero else 10000000,'token_balance':0 if zero else 5000}
        original=fixture.run(case);candidate=fixture.run(case,args.candidate)
        fields=['error','accounts','events','inner','return_data']
        rows.append({'name':str(case),'different_fields':[key for key in fields if original[key]!=candidate[key]],'original':original,'candidate':candidate})
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'scope':__doc__,'fixture_sha256':sha(Path(__file__)),'base_fixture_sha256':sha(ROOT/'scripts/pump_cashback_differential.py'),'candidate_sha256':sha(args.candidate),'original_sha256':sha(ROOT/'evidence/original/pump/deployed.so'),'case_count':len(rows),'mismatches':[i for i,row in enumerate(rows) if row['different_fields']],'cases':rows}
args.output.write_bytes(gzip.compress(json.dumps(report,indent=2).encode(),mtime=0));print([(row['name'],row['original']['error'],row['candidate']['error'])for row in rows])
if report['mismatches']:raise SystemExit(1)
