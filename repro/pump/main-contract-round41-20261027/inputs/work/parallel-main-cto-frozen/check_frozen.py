"""Signed CTO shared-vault freeze matrix using captured dependencies."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import pump_admin_cto_differential as fixture
parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
rows=[]
for holder in [False,True]:
    for stable in [False,True]:
        for account in ['creator_vault_quote_token_account','coin_creator_vault_ata']:
            for amount in [0,1]:
                for state in [1,2]:
                    case={'holder':holder,'new_none':holder,'global_patches':[(1086,'01')],
                          'accounts':{account:{'tokens':amount,'patches':[(108,bytes([state]).hex())]}}}
                    if stable:case['quote']=str(fixture.Pubkey.from_bytes(bytes([88])*32))
                    name=f'holder={holder}/stable={stable}/{account}/amount={amount}/state={state}'
                    original=fixture.run(case);candidate=fixture.run(case,args.candidate)
                    fields=['error','before','after','events','inner','return']
                    rows.append({'name':name,'case':case,'different_fields':[key for key in fields if original[key]!=candidate[key]],'original':original,'candidate':candidate})
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'scope':__doc__,'candidate_sha256':sha(args.candidate),'original_sha256':sha(ROOT/'evidence/original/pump/deployed.so'),'fixture_sha256':sha(Path(__file__)),'base_fixture_sha256':sha(ROOT/'scripts/pump_admin_cto_differential.py'),'case_count':len(rows),'mismatches':[i for i,row in enumerate(rows)if row['different_fields']],'cases':rows}
args.output.write_bytes(gzip.compress(json.dumps(report,indent=2).encode(),mtime=0));print(len(rows),[(row['name'],row['original']['error'],row['candidate']['error'],row['different_fields'])for row in rows if row['different_fields']])
if report['mismatches']:raise SystemExit(1)
