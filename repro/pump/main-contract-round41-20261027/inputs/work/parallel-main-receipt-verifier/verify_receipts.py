#!/usr/bin/env python3
"""CLI for the private read-only Pump receipt verifier."""
from pathlib import Path
import argparse,hashlib,json
from receipt_verifier import verify_reports
P=Path(__file__).resolve().parent;R=next((p for p in P.parents if(p/'evidence/upstream/pump.json').is_file()),Path.cwd())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--full',type=Path,required=True);p.add_argument('--additional',type=Path,required=True);p.add_argument('--idl',type=Path);p.add_argument('--root',type=Path,default=R);p.add_argument('--candidate-sha256');p.add_argument('--expected-total',type=int);p.add_argument('--substitutions',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=verify_reports(a.full,a.additional,a.idl or a.root/'evidence/upstream/pump.json',root=a.root,candidate_sha256=a.candidate_sha256,expected_total=a.expected_total,substitution_path=a.substitutions)
 result['verifier_sha256']={x.name:hashlib.sha256(x.read_bytes()).hexdigest()for x in [P/'receipt_verifier.py',Path(__file__)]};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'counts':result['counts'],'main_attribution':result['main_attribution'],'findings':len(result['findings'])},indent=2));return 0 if result['status']=='passed'else 1
if __name__=='__main__':raise SystemExit(main())
