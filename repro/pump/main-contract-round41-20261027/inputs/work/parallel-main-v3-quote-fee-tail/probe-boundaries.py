"""Signed V3 fee-config payload boundary107/109/111 bytes."""
from pathlib import Path
import sys,json,gzip,argparse,hashlib,inspect
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_token_extensions_differential as h
from pump_diagnostic_audit import audit
source=inspect.getsource(h.run);needle='        blob=ac.data[:82]+bytes(83)+bytes([1])+struct.pack(\'<HH\',1,len(conf))+conf';assert source.count(needle)==1;source=source.replace(needle,"        extra=c.get('config_extra',0)\n        conf=conf[:len(conf)+extra] if extra<0 else conf+bytes(extra)\n"+needle);ns=dict(h.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);run=ns['run']
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for op in ['buy_v3','buy_exact_quote_in_v3','sell_v3']:
 for extra in [-1,1,3]:
  c={'name':f'{op}-length-{108+extra}','operation':op,'token_quote':True,'quote2022':True,'replace':13,'reserve_in':h.base_in,'reserve_out':h.base_out,'user_lamports':10**16,'extension':True,'bps':100,'config_extra':extra,'amount':10**9 if op!='sell_v3'else 500000000,'max_cost':10**12 if op=='buy_v3'else 0 if op=='sell_v3'else 1}
  o=run(R/'evidence/original/pump/deployed.so',c);n=run(a.candidate,c);assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'transformed_fixture_sha256':hashlib.sha256(source.encode()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,x in enumerate(rows)if x['different_fields']]};r['diagnostics']=audit({'boundaries':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0))
