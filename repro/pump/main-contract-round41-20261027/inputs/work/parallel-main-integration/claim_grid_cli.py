"""Signed offline claim overflow probes with complete LiteSVM logs retained.

The historical fixture discarded Left/Right lines from its returned relevant_logs.
This adapter adds complete logs only when needed; transaction construction and
execution are unchanged.
"""
from pathlib import Path
import sys,inspect,json,gzip,hashlib,re,argparse

ROOT=Path(__file__).resolve().parents[2];w=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
sys.path.insert(0,str(ROOT/'scripts'))
import pump_claim_token_incentives_differential as fixture
source=inspect.getsource(fixture.run_case)
old='return {"case": case, "error": error,'
if old in source:
    source=source.replace(old,'return {"logs": logs, "case": case, "error": error,')
else:
    assert 'return {"logs": logs, "case": case, "error": error,' in source
exec(compile(source,str(Path(__file__)), 'exec'),fixture.__dict__)

cases=[]
for volume in (0,1,2**32,2**63-1,2**63,2**64-1):
 for supply in (0,1,2,2**32,2**64-1):
  for total in (0,1,2**32,2**64-1):
   cases.append(dict(name=f"claim-wide-{volume}-{supply}-{total}",now=1,last=0,volume=volume,supply=supply,day_volume=total,vault_amount=2**64-1))
for pending in (0,1,2**64-2,2**64-1):
 for claimed in (0,1,2**64-1):
  cases.append(dict(name=f"claim-pending-{pending}-{claimed}",now=1,last=0,unclaimed=pending,claimed=claimed,volume=1,supply=1,day_volume=1,vault_amount=2**64-1))

rows=[]
def diagnostics(x):
    return [re.sub(r' thrown in .*?:\d+\.', '.',line) for line in x['logs']
            if any(s in line for s in ['AnchorError','Left:','Right:'])] + [line.split('\n',1)[-1] for line in x['logs'] if line.startswith('Program log: panicked at ')]
for case in cases:
    a=fixture.run_case(fixture.ORIGINAL,case)
    b=fixture.run_case(args.candidate,case)
    fields=['error','error_code','success','transaction_base64','before','after','user_after','event_data_base64','inner']
    diff=[field for field in fields if a[field]!=b[field]]
    if diagnostics(a)!=diagnostics(b):diff.append('diagnostics')
    rows.append(dict(case=case,original=a,candidate=b,differences=diff))
    if diff: print(json.dumps(dict(case=case['name'],original_diagnostics=diagnostics(a),candidate_diagnostics=diagnostics(b),differences=diff)))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=dict(scope=__doc__,original_sha256=sha(fixture.ORIGINAL),candidate_sha256=sha(args.candidate),
            adapter_sha256=sha(Path(__file__)),fixture_sha256=sha(Path(fixture.__file__)),cases=rows)
args.output.write_bytes(gzip.compress(json.dumps(record).encode(),mtime=0))

print(json.dumps({'case_count':len(rows),'mismatch_count':sum(bool(r['differences']) for r in rows)}))
assert all(not r['differences'] for r in rows)
