"""Signed Sweep regression corpus, excluding account-owner mutation cases."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
import pump_fee_sweep_differential as m
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for c in m.cases():
 if any('owner' in spec for spec in c.get('patch',{}).values()):continue
 assert all('owner' not in x for x in c.get('patch',{}).values())
 start=len(loader.LOADS);o=m.run(c);n=m.run(c,a.candidate);loads=loader.LOADS[start:]
 diff=[k for k in ['error','before','after'] if o[k]!=n[k]]
 diff += [k for k in ['return_data','inner_instructions'] if o['metadata'][k]!=n['metadata'][k]]
 if [x for x in o['logs'] if x.startswith('Program data: ')] != [x for x in n['logs'] if x.startswith('Program data: ')]:diff.append('events')
 rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loads})
 if diff:print(json.dumps({'case':c,'different_fields':diff,'original_error':o['error'],'candidate_error':n['error']}),flush=True)
d=audit({'sweeps':rows});out={'case_count':len(rows),'suites':{'sweeps':rows},'diagnostics':d,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};a.output.write_bytes(gzip.compress(json.dumps(out).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(out['mismatches']),'strict_mismatches':len(d['mismatches'])}),flush=True)
