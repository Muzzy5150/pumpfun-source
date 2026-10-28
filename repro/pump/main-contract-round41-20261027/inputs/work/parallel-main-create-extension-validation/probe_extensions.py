"""Signed CreateV2 quote TLV padding, uniqueness, and partial-tail boundary probes."""
from pathlib import Path
import sys,json,gzip,hashlib,argparse,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
import pump_create_quote_differential as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
def diag(r):return[re.sub(r' thrown in .*?:\d+\.', '.',s)for s in r['logs']if 'AnchorError' in s or 'Left:' in s or 'Right:' in s]
base={'instruction':'create_v2','quote':True,'quote_token22':True}
cases=[]
def add(name,extensions,mutations=None):cases.append(dict(base,case=name,quote_extensions=[(t,b.hex())for t,b in extensions],**({'mutations':{'quote_mint':mutations}} if mutations else {})))
add('valid-pointer',[(18,bytes(64))])
for at in [82,123,164]:add(f'padding-{at}',[(18,bytes(64))],{'patches':[(at,'01')]})
for t,b in [(1,bytes(108)),(4,bytes(65)),(6,b'\1'),(12,bytes(32)),(14,bytes(64)),(16,bytes(129)),(18,bytes(64)),(19,b''),(25,bytes(56)),(26,bytes(33))]:add(f'duplicate-{t}',[(t,b),(t,b)])
for pair in [(18,19),(4,12),(1,18)]:add(f'unique-{pair[0]}-{pair[1]}',[(t,bytes({18:64,19:0,4:65,12:32,1:108}[t]))for t in pair])
for size in [166,167,168,169]:add(f'length-{size}',[(18,bytes(64))],{'length':size})
for value in ['00','01','7f','ff']:add(f'partial-tail-{value}',[(18,bytes(64))],{'length':235,'patches':[(234,value)]})
add('unknown-duplicate',[(29,b''),(29,b'')])
for c in cases:
 o=h.run(c);n=h.run(c,a.candidate);assert o['transaction_base64']==n['transaction_base64'];diff=[k for k in ['error','before','after','events','inner','return']if o[k]!=n[k]];diff+=['diagnostics']if diag(o)!=diag(n)else[];rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(json.dumps({'case':c['case'],'original_error':o['error'],'candidate_error':n['error'],'diff':diff}),flush=True)
r={'scope':__doc__,'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256(h.ORIGINAL.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'case_count':len(rows),'mismatches':[x['case']['case']for x in rows if x['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(r).encode(),mtime=0));print(json.dumps({'case_count':len(rows),'mismatches':r['mismatches']}))
