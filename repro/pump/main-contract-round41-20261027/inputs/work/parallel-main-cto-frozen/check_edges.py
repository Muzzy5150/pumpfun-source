"""Shared CTO vault decode and multi-fault ordering probes."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import pump_admin_cto_differential as fixture
parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
specs=[]
for stable in [False,True]:
    quote={'quote':str(fixture.Pubkey.from_bytes(bytes([88])*32))} if stable else {}
    base={'holder':True,'new_none':True,'global_patches':[(1086,'01')],**quote}
    for account in ['creator_vault_quote_token_account','coin_creator_vault_ata']:
        for amount in [0,1]:
            for state in [0,3,255]:
                specs.append((f'malformed/{stable}/{account}/{amount}/{state}',{**base,'accounts':{account:{'tokens':amount,'patches':[(108,bytes([state]).hex())]}}}))
    for amm_amount,pump_amount in [(0,0),(0,1),(1,0),(1,1)]:
        specs.append((f'both-frozen/{stable}/{amm_amount}/{pump_amount}',{**base,'accounts':{'coin_creator_vault_ata':{'tokens':amm_amount,'patches':[(108,'02')]},'creator_vault_quote_token_account':{'tokens':pump_amount,'patches':[(108,'02')]}}}))
    for pump_amount in [0,1]:
        specs.append((f'amm-live-pump-frozen/{stable}/{pump_amount}',{**base,'accounts':{'coin_creator_vault_ata':{'tokens':1},'creator_vault_quote_token_account':{'tokens':pump_amount,'patches':[(108,'02')]}}}))
    for account in ['creator_vault_quote_token_account','coin_creator_vault_ata']:
        specs.append((f'disabled-holder/{stable}/{account}',{**base,'global_patches':[(1086,'00')],'accounts':{account:{'tokens':1,'patches':[(108,'02')]}}}))
rows=[]
for name,case in specs:
    original=fixture.run(case);candidate=fixture.run(case,args.candidate)
    fields=['error','before','after','events','inner','return']
    rows.append({'name':name,'case':case,'different_fields':[key for key in fields if original[key]!=candidate[key]],'original':original,'candidate':candidate})
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'scope':__doc__,'candidate_sha256':sha(args.candidate),'original_sha256':sha(ROOT/'evidence/original/pump/deployed.so'),'fixture_sha256':sha(Path(__file__)),'base_fixture_sha256':sha(ROOT/'scripts/pump_admin_cto_differential.py'),'case_count':len(rows),'mismatches':[i for i,row in enumerate(rows)if row['different_fields']],'cases':rows}
args.output.write_bytes(gzip.compress(json.dumps(report,indent=2).encode(),mtime=0));print(len(rows),[(row['name'],row['original']['error'],row['candidate']['error'],row['different_fields'])for row in rows if row['different_fields']])
if report['mismatches']:raise SystemExit(1)
