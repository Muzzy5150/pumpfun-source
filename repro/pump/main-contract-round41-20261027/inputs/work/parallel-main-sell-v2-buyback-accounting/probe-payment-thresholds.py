"""Signed SellV2 native/token payment boundaries; balances only, no owner changes."""
from pathlib import Path
import argparse,gzip,hashlib,json,struct,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-loader-optimized'))
import pump_captured_loader as loader
loader.install()
import pump_sell_v2_differential as m
from pump_diagnostic_audit import audit
from solders.rent import Rent
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
amount=10**12;vbase,vquote=struct.unpack_from('<QQ',m.INITIAL[m.CURVE].data,8);quote=amount*vquote//(vbase+amount);pf=(quote*95+9999)//10000;cf=(quote*30+9999)//10000;output=quote-pf-cf;rent=Rent.default().minimum_balance(166)
assert (quote,pf,cf)==(27933012,265364,83800)
cases=[]
for token in [False,True]:
 for balance in ([0,cf-1,cf] if token else [])+[output-1,output,output+cf-1,output+cf,quote-1,quote]:
  for bps in [0,20000]:
   mut={'global':{'u64':[[997,bps]]},'bonding_curve':{'u64':[[32,10**12]]},'associated_base_user':{'u64':[[64,10**15]]}}
   if token:mut['associated_quote_bonding_curve']={'u64':[[64,balance]]}
   else:mut['bonding_curve']['lamports']=balance-rent
   cases.append({'name':f'payment_threshold_{token}_{balance}_{bps}','amount':amount,'token_quote':token,'account_mutations':mut})
for token in [False,True]:
 for bps in [0,20000]:
  mut={'global':{'u64':[[997,bps]]}}
  if token:mut['associated_creator_vault']={'u64':[[64,2**64-1]]}
  else:mut['creator_vault']={'lamports':2**64-1}
  cases.append({'name':f'creator_credit_overflow_{token}_{bps}','token_quote':token,'account_mutations':mut})
for fee in [0,250]:
 for cashback in [False,True]:
  for bps in [0,20000]:
   cases.append({'name':f'token22_fee_{fee}_cashback_{cashback}_{bps}','token_quote':True,'token22':True,'transfer_fee_bps':fee,'max_fee':7,'curve_bytes':[[82,int(cashback)]],'account_mutations':{'global':{'u64':[[997,bps]]}}})
for c in cases:
 start=len(loader.LOADS);o=m.run(c);n=m.run(c,a.candidate);loads=loader.LOADS[start:];assert len(loads)==2;diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loads})
 if diff:print(json.dumps({'case':c['name'],'diff':diff,'original':o['error'],'candidate':n['error']}),flush=True)
d=audit({'sell_v2_payment_thresholds':rows});r={'case_count':len(rows),'suites':{'sell_v2_payment_thresholds':rows},'diagnostics':d,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'mismatches':[i for i,x in enumerate(rows) if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'cases':len(rows),'mismatches':len(r['mismatches']),'strict_mismatches':len(d['mismatches'])}),flush=True)
