"""Signed partial-balance error-order control for legacy sell; no owner changes."""
from pathlib import Path
import argparse,gzip,hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
import pump_legacy_sell_differential as m
from solders.rent import Rent
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
amount=10**12;vbase,vquote=struct.unpack_from('<QQ',m.INITIAL[m.CURVE].data,8);quote=amount*vquote//(vbase+amount);initial=quote-Rent.default().minimum_balance(166)-1
assert initial>0
for bps in [0,20000]:
 c={'name':f'sell_partial_balance_{bps}','amount':amount,'account_mutations':{'global':{'u64':[[997,bps]]},'bonding_curve':{'lamports':initial,'u64':[[32,10**12]]},'associated_user':{'u64':[[64,10**15]]}}}
 start=len(loader.LOADS);o=m.run(c);n=m.run(c,a.candidate);loads=loader.LOADS[start:];assert len(loads)==2;diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loads})
 if diff:print(json.dumps({'case':c['name'],'diff':diff,'original':o['error'],'candidate':n['error']}),flush=True)
d=audit({'sell_partial_balance':rows});r={'case_count':len(rows),'suites':{'sell_partial_balance':rows},'diagnostics':d,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'mismatches':[i for i,x in enumerate(rows) if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(r['mismatches']),'strict_mismatches':len(d['mismatches'])}),flush=True)
