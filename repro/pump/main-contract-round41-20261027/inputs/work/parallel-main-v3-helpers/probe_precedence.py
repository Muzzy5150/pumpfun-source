"""Signed V3 compound-fault ordering probes from original validation helper calls."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as f
from pump_diagnostic_audit import audit
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-match',action='store_true');a=p.parse_args();rows=[]
changes=[('control',{}),('complete_and_cashback',{'flags':[48,82]}),('complete_and_quote_mint',{'flags':[48],'token_quote':True,'replace':13,'quote_mutation':'user_mint'}),('zero_and_quote_mint',{'amount':0,'token_quote':True,'replace':13,'quote_mutation':'user_mint'}),('cashback_and_quote_authority',{'flags':[82],'token_quote':True,'replace':13,'quote_mutation':'user_authority'}),('complete_only',{'flags':[48]})]
for op in ['buy_v3','sell_v3','buy_exact_quote_in_v3']:
 for label,change in changes:
  c={'operation':op,'reserve_in':f.base_in,'reserve_out':f.base_out,'amount':500000000,'max_cost':10**12 if op=='buy_v3'else 1 if op=='buy_exact_quote_in_v3'else 0,'user_lamports':10**16,**change};o=f.run(R/'evidence/original/pump/deployed.so',c);n=f.run(a.candidate,c);diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':{'label':label,**c},'original':o,'candidate':n,'different_fields':diff});print(op,label,o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'case_count':len(rows),'cases':rows,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'mismatches':[i for i,row in enumerate(rows)if row['different_fields']]};r['diagnostics']=audit({'precedence':r});a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print({'cases':len(rows),'mismatches':r['mismatches'],'strict_mismatches':len(r['diagnostics']['mismatches'])})
if a.require_match:assert not r['mismatches']and not r['diagnostics']['mismatches']
