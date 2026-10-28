"""Signed V3 full TLV scan behavior for the extracted unit-error parser."""
from pathlib import Path
import sys,json,gzip,inspect,argparse,hashlib
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_v3_token_extensions_differential as h
from pump_diagnostic_audit import audit
source=inspect.getsource(h.run);needle="        if 'mint_length' in c:blob=blob[:c['mint_length']]";assert source.count(needle)==1
addition='''        known=blob[166:]
        unknown=struct.pack('<HH',65000,3)+b'abc'
        shape=c['shape']
        if shape=='unknown_before':blob=blob[:166]+unknown+known
        elif shape=='unknown_after':blob+=unknown
        elif shape=='duplicate':blob+=known
        elif shape=='malformed_after':blob+=struct.pack('<HH',65000,9)+b'abc'
        elif shape=='one_tail':blob+=b'x'
        elif shape=='zero_terminator':blob+=bytes(2)+struct.pack('<HH',65000,9)+b'abc'
''';source=source.replace(needle,addition+needle);ns=dict(h.__dict__);exec(compile(source,str(Path(__file__)),'exec'),ns);run=ns['run']
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for op in ['buy_v3','buy_exact_quote_in_v3','sell_v3']:
 for shape in ['unknown_before','unknown_after','duplicate','malformed_after','one_tail','zero_terminator']:
  c={'name':f'{op}-{shape}','shape':shape,'operation':op,'token_quote':True,'quote2022':True,'replace':13,'reserve_in':h.base_in,'reserve_out':h.base_out,'user_lamports':10**16,'extension':True,'bps':100,'amount':10**9 if op!='sell_v3'else 500000000,'max_cost':10**12 if op=='buy_v3'else 0 if op=='sell_v3'else 1}
  o=run(R/'evidence/original/pump/deployed.so',c);n=run(a.candidate,c);assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['name'],o['error'],n['error'],diff,flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'transformed_fixture_sha256':hashlib.sha256(source.encode()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,x in enumerate(rows)if x['different_fields']]};r['diagnostics']=audit({'tlv-shapes':r});a.output.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0))
