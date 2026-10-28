#!/usr/bin/env python3
"""Normally signed main CreateV2 gate ordering and quote policy; companion is only invoked as captured dependency."""
from pathlib import Path
import json,gzip,hashlib,argparse,base64,re
from solders.transaction import VersionedTransaction
import nested_fixture as h
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();defs=Path(__file__).with_name('policy-precedence-cases.json');cases=json.loads(defs.read_text());paths=[Path(__file__),Path(h.__file__),defs,a.candidate,h.ORIGINAL];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(p):sha(p)for p in paths};rows=[]
def logs(x):return[re.sub(r'AnchorError thrown in [^\n]+?:\d+\.', 'AnchorError thrown in <source>.',s)for s in x['logs']if not re.fullmatch(r'Program \S+ consumed \d+ of \d+ compute units',s)]
for c in cases:
 x=h.run(c);y=h.run(c,a.candidate);assert x['transaction_base64']==y['transaction_base64'];tx=VersionedTransaction.from_bytes(base64.b64decode(x['transaction_base64']));assert all(tx.verify_with_results())and len(tx.signatures)==tx.message.header.num_required_signatures
 diff=[k for k in ['error','before','after','events','inner','return']if x[k]!=y[k]]
 if logs(x)!=logs(y):diff.append('semantic_logs')
 rows.append({'case':c,'original':x,'candidate':y,'different_fields':diff,'verified_signature_count':len(tx.signatures)});print(c['case'],x['error'],y['error'],diff,flush=True)
assert before=={str(p):sha(p)for p in paths};d={'scope':__doc__,'candidate_sha256':sha(a.candidate),'input_sha256':before,'case_count':len(rows),'cases':rows,'mismatches':[r['case']['case']for r in rows if r['different_fields']]};a.output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0));print('cases',len(rows),'mismatches',len(d['mismatches']))
