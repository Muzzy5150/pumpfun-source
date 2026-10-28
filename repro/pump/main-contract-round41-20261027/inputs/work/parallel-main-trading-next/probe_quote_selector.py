from pathlib import Path
import argparse,base64,gzip,hashlib,json
import quote_fixture as h
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
QUOTE2=str(h.f.Pubkey(bytes([131,13,252,159,222,95,230,184,170,124,4,164,118,233,30,138,198,187,38,74,173,144,250,25,201,223,73,216,92,62,91,94])))
def cases():
 for quote in [None,'So11111111111111111111111111111111111111112','EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v','Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',str(h.f.Pubkey(bytes([56])*32)),QUOTE2]:
  for mode in ['modern','exotic_zero','legacy','stable']:
   for op in ['buy_v3','sell_v3','buy_exact_quote_in_v3']:
    c={'name':f'{quote}_{mode}_{op}','operation':op,'amount':10**9 if op!='sell_v3' else 500000000,'max_cost':10**12 if op=='buy_v3' else 0 if op=='sell_v3' else 1,'reserve_in':h.base_in,'reserve_out':h.base_out,'user_lamports':10**16,'selector_mode':mode}
    if quote:c.update(quote_address=quote,token_quote=True,quote2022=False,replace=13)
    yield c

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[];orig=R/'evidence/original/pump/deployed.so'
 for c in cases():
  o=h.run(orig,c);r={'case':c,'original':o}
  if a.candidate:
   b=h.run(a.candidate,c);diff=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data'] if o[k]!=b[k]];r.update(candidate=b,different_fields=diff,match=not diff)
  rows.append(r)
  rates=None
  if o['event_payloads']:
   ev=base64.b64decode(o['event_payloads'][0]);rates=[int.from_bytes(ev[161:169],'little'),int.from_bytes(ev[209:217],'little')]
  print(c['name'],o['error'],rates,r.get('different_fields'),flush=True)
 d={'scope':'Synthetic offline quote fee-selector cases; real captured dependencies and normally signed transactions.','original_sha256':hashlib.sha256(orig.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest() if a.candidate else None,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(h.__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r.get('match') is False]}
 a.output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
