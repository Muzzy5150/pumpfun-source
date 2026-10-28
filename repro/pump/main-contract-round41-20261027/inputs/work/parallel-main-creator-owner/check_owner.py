"""Signed creator owner edge cases for both collection entrypoints."""
import argparse, gzip, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from solders.pubkey import Pubkey
FEES = Pubkey.from_string('pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ')
import pump_creator_collect_v2_differential as v2
base = ROOT / 'scripts/pump_creator_collect_differential.py'
source = base.read_text().split('\ndef cases():', 1)[0]
needle = ' creator_before=vm.get_account(creator)'
assert source.count(needle) == 1
source = source.replace(needle, " ac=vm.get_account(creator);vm.set_account(creator,Account(ac.lamports,ac.data,FEES,ac.executable))\n" + needle)
namespace = {'__file__': str(base), 'FEES': FEES}
exec(compile(source, str(base), 'exec'), namespace)
parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
rows=[]
for amount in [0, 890880, 1000000, 10**9]:
    original=namespace['execute'](ROOT/'evidence/original/pump/deployed.so','none',amount)
    candidate=namespace['execute'](args.candidate,'none',amount)
    fields=[key for key in original if key not in ['logs','transaction_base64']]
    rows.append({'name':f'v1/fees_owner/{amount}','different_fields':[key for key in fields if original[key]!=candidate[key]],'original':original,'candidate':candidate})
for quote in [v2.WSOL,v2.QUOTE]:
    case={'quote':str(quote),'patch':{'creator':{'owner':str(FEES)}}}
    original=v2.run(case);candidate=v2.run(case,args.candidate)
    fields=['error','before','after','events','inner','returns']
    rows.append({'name':f'v2/fees_owner/{"native" if quote==v2.WSOL else "token"}','different_fields':[key for key in fields if original[key]!=candidate[key]],'original':original,'candidate':candidate})
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'scope':__doc__,'candidate_sha256':sha(args.candidate),'original_sha256':sha(ROOT/'evidence/original/pump/deployed.so'),'fixture_sha256':sha(Path(__file__)),'base_fixture_sha256':sha(base),'v2_fixture_sha256':sha(ROOT/'scripts/pump_creator_collect_v2_differential.py'),'case_count':len(rows),'mismatches':[i for i,row in enumerate(rows) if row['different_fields']],'cases':rows}
args.output.write_bytes(gzip.compress(json.dumps(report,indent=2).encode(),mtime=0));print([(row['name'],row['original']['error'],row['candidate']['error'],row['different_fields']) for row in rows])
if report['mismatches']:raise SystemExit(1)
