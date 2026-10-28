"""Signed preexisting migration quote-account balance and close behavior."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import pump_migrate_v2_probe as p
parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
rows=[]
for stable,amount,lamports in [(False,0,10_000_000),(False,1,10_000_000),(False,2**64-1,10_000_000),(False,0,2_039_280),(False,1,2_039_281),(True,0,10_000_000),(True,1,10_000_000)]:
    mint=p.Pubkey.from_bytes(bytes([217])*32)if stable else p.WSOL
    authority=p.pda([b'pool-authority',bytes(p.MINT)],p.P)
    data=bytearray(165);data[:32]=bytes(mint);data[32:64]=bytes(authority);data[64:72]=amount.to_bytes(8,'little');data[108]=1
    if not stable:data[109:113]=(1).to_bytes(4,'little');data[113:121]=(2_039_280).to_bytes(8,'little')
    case={'boost':True,'stable':stable,'mutations':{'pool_authority_quote_account':{'owner':str(p.TOKEN),'lamports':lamports,'patches':[(0,data.hex())]}}}
    original=p.run(case);candidate=p.run(case,args.candidate)
    for value in [original,candidate]:value['events']=[line for line in value['logs']if line.startswith('Program data:')]
    fields=['error','before','after','events','inner','return']
    rows.append({'name':f'{stable}/{amount}/{lamports}','case':case,'mismatched_fields':[key for key in fields if original[key]!=candidate[key]],'original':original,'candidate':candidate})
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'scope':__doc__,'case_count':len(rows),'candidate_sha256':sha(args.candidate),'original_sha256':sha(ROOT/'evidence/original/pump/deployed.so'),'fixture_sha256':sha(Path(__file__)),'base_fixture_sha256':sha(ROOT/'scripts/pump_migrate_v2_probe.py'),'cases':rows,'mismatches':[i for i,row in enumerate(rows)if row['mismatched_fields']]}
args.output.write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0));print([(row['name'],row['original']['error'],row['candidate']['error'],row['mismatched_fields'])for row in rows if row['mismatched_fields']])
if report['mismatches']:raise SystemExit(1)
