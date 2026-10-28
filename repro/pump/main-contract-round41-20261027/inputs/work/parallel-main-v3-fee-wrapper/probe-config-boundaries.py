"""Signed V3 typed fee-config length, quote-family, and whitelist controls."""
from pathlib import Path
import inspect,sys,json,gzip,hashlib,argparse,struct
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_configured_fee_differential as h
from pump_diagnostic_audit import audit
source=inspect.getsource(h.run);needle="quote=f.Pubkey.from_string('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')";assert source.count(needle)==1;source=source.replace(needle,"quote=f.Pubkey(bytes([84])*32) if c.get('exotic') else f.Pubkey.from_string('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')")
ns=dict(h.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);run=ns['run']
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
def fees(p,c):return struct.pack('<QQQ',0,p,c)
def tiers(p,c):return struct.pack('<I',1)+bytes(16)+fees(p,c)
for op in ['buy_v3','buy_exact_quote_in_v3','sell_v3']:
 for family in ['native','stable','exotic']:
  for length in [100,2511,2512,4072,4073,4096,4097,4352]:
   for waived in [False,True]:
    old={k:h.initial[k]for k in [h.fee_key,h.global_key]}
    try:
     ac=old[h.fee_key];encoded=ac.data[:41]+fees(700,80)+tiers(90,30)+tiers(180,60)+fees(400,120);h.initial[h.fee_key]=h.f.Account(ac.lamports,encoded.ljust(4352,b'\0'),ac.owner)
     if waived:
      g=old[h.global_key];d=bytearray(g.data);d[451:483]=bytes(h.user.pubkey());h.initial[h.global_key]=h.f.Account(g.lamports,bytes(d),g.owner)
     c={'name':f'{op}-{family}-{length}-waived-{waived}','operation':op,'reserve_in':h.base_in,'reserve_out':h.base_out,'amount':500000000 if op=='sell_v3'else 10**9,'max_cost':0 if op=='sell_v3'else 10**12 if op=='buy_v3'else 1,'token_quote':family!='native','exotic':family=='exotic','replace':13,'user_lamports':10**16,'fee_len':length}
     o=run(R/'evidence/original/pump/deployed.so',c);n=run(a.candidate,c)
    finally:h.initial.update(old)
    assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256((R/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'transformed_run_sha256':hashlib.sha256(source.encode()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows)if r['different_fields']]};r['diagnostics']=audit({'config_boundaries':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));print(json.dumps({'count':len(rows),'mismatches':r['mismatches'],'diagnostics':len(r['diagnostics']['mismatches'])}))
