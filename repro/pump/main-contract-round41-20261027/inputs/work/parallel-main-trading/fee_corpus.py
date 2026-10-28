"""New synthetic offline v2 quote transfer-fee boundaries, original ELF as oracle."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import buy_v2_fixture as h

def cases():
 rows=[]
 for kind in ['buy_v2','buy_exact_quote_in_v2']:
  base={'kind':kind,'token_quote':True,'token22':True,'amount':10**9}
  for bps,cap in [(0,0),(1,1),(1,2**64-1),(100,2**64-1),(250,7),(250,2**64-1),(10000,0),(10000,1),(10000,2**64-1)]:
   for amount in [0,1,2,1000,10**9,10**12]:rows.append({**base,'name':f'{kind}_fee_{bps}_{cap}_{amount}','transfer_fee_bps':bps,'max_fee':cap,'amount':amount})
  for epoch in [0,4,5,6]:rows.append({**base,'name':f'{kind}_epoch_{epoch}','transfer_fee_bps':1,'new_epoch':5,'new_bps':250,'new_max_fee':7,'epoch':epoch})
  for length in [82,165,166,169,170,277,278]:rows.append({**base,'name':f'{kind}_mint_length_{length}','transfer_fee_bps':100,'account_mutations':{'quote_mint':{'length':length}}})
  for flags in [[[82,1]],[[81,1]],[[124,1]]]:rows.append({**base,'name':f'{kind}_flags_{flags}','transfer_fee_bps':100,'curve_bytes':flags,'reserved':flags==[[81,1]]})
  for partial in [0,1]:
   for amount in ([793099000000000,793099000000001] if kind=='buy_v2' else [10**11,10**12]):
    rows.append({**base,'name':f'{kind}_completion_{amount}_{partial}','amount':amount,'transfer_fee_bps':100,'trailing':[partial]})
 for limit in [28310,28592,28593,28594]:rows.append({'name':f'buy_cost_{limit}','kind':'buy_v2','token_quote':True,'token22':True,'amount':10**9,'minimum':limit,'transfer_fee_bps':100})
 for limit in [33867943546787,33867943546788,33867943546789]:rows.append({'name':f'exact_out_{limit}','kind':'buy_exact_quote_in_v2','token_quote':True,'token22':True,'amount':10**9,'minimum':limit,'transfer_fee_bps':100})
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--candidate',type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();rows=[]
 for c in cases():
  o=h.run(c);r={'case':c,'original':o}
  if a.candidate:
   b=h.run(c,a.candidate);diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=b[k]];r.update(candidate=b,match=not diff,different_fields=diff)
  rows.append(r);print(c['name'],o['error'],r.get('different_fields'),flush=True)
 d={'scope':__doc__,'original_sha256':hashlib.sha256((ROOT/'evidence/original/pump/deployed.so').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest() if a.candidate else None,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(h.__file__).read_bytes()).hexdigest(),'case_count':len(rows),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r.get('match') is False]};a.output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0));print(d['case_count'],d['mismatches'])
if __name__=='__main__':main()
