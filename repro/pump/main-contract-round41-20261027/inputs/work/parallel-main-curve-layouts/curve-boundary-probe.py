#!/usr/bin/env python3
"""Signed captured-loader migration probes across every historical curve boundary.

Compares original and candidate errors, events, inner calls, return data and
complete before/after account snapshots. This is bounded synthetic evidence.
"""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import pump_migrate_v2_probe as fixture

def cases():
 for n in [0,7,8,48,49,50,80,81,82,83,114,115,123,124,125,140,141,165,166]:
  for flag in ([None]if n<49 else[0,1,2,255]):
   patches=[]if flag is None else[(48,bytes([flag]).hex())]
   yield {'name':f'curve-wire-{n}-complete-{flag}','boost':True,'mutations':{'bonding_curve':{'length':n,'patches':patches}}}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();candidate=a.candidate.resolve();paths=[Path(__file__).resolve(),Path(fixture.__file__).resolve(),candidate,ROOT/'evidence/original/pump/deployed.so'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(p):sha(p)for p in paths};rows=[]
 for c in cases():
  x,y=fixture.run(c),fixture.run(c,candidate)
  for result in [x,y]:
   result['events']=[line for line in result['logs']if line.startswith('Program data:')]
   assert result['signature_verification']
  keys=['error','before','after','inner','return','events'];diff=[k for k in keys if x[k]!=y[k]];rows.append({'case':c,'original':x,'candidate':y,'different_fields':diff})
 assert before=={str(p):sha(p)for p in paths}
 result={'scope':__doc__,'inputs_sha256':before,'candidate_sha256':sha(candidate),'original_sha256':sha(ROOT/'evidence/original/pump/deployed.so'),'case_count':len(rows),'cases':rows,'mismatches':[r['case']['name']for r in rows if r['different_fields']]};a.output.write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps({'cases':len(rows),'mismatches':result['mismatches']}));assert not result['mismatches']
if __name__=='__main__':main()
