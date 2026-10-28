from pathlib import Path
import base64,gzip,hashlib,json
P=Path(__file__).resolve().parent;R=P.parents[1]
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def key(row):
 state={}
 for label,a in row['before'].items():
  if a is None:continue
  address=a.get('address',label)
  d={n:a[n]for n in ['owner','lamports','executable','rent_epoch']if n in a}
  if 'data_base64'in a:d['data_hex']=base64.b64decode(a['data_base64']).hex()
  elif 'data'in a:d['data_hex']=a['data']
  if address in state:assert state[address]==d
  state[address]=d
 return hashlib.sha256((row['transaction_base64']+json.dumps(state,sort_keys=True,separators=(',',':'))).encode()).hexdigest()
def originals(v):
 if isinstance(v,dict):
  x=v.get('original',v.get('target'))
  if isinstance(x,dict)and'transaction_base64'in x and'before'in x:yield x
  else:
   for k,x in v.items():
    if k not in ('candidate',):yield from originals(x)
 elif isinstance(v,list):
  for x in v:yield from originals(x)
current=[]
for folder in ['full','additional']:
 for f in sorted((R/'work/parallel-main-integration/round32-unified/suites'/folder).glob('*.json.gz')):
  if 'claim' in f.name:current.append(f)
prior={};inputs={};counts={}
for f in current:
 rows=list(originals(read(f)));counts[str(f.relative_to(R))]=len(rows);inputs[str(f.relative_to(R))]=hashlib.sha256(f.read_bytes()).hexdigest()
 for o in rows:prior.setdefault(key(o),[]).append(str(f.relative_to(R)))
assert sum(counts.values())==498,counts
newread=read(P/'compound-before.json.gz');new=[];overlap=[];seen=set()
for row in newread['cases']:
 k=key(row['original']);record={'case':row['case'],'input_hash':k}
 if k in prior:record['matches']=prior[k];overlap.append(record)
 elif k in seen:raise AssertionError('new duplicate')
 else:new.append(record);seen.add(k)
report={'scope':'Input dedup against six authoritative Round32 claim suites (498 executions); exact signed transaction + canonical address-keyed non-null watched pre-state, including owner/lamports/data/executable/rent_epoch. Retains repeated historical cases only as provenance.','existing_cases':498,'existing_unique_inputs':len(prior),'new_executed_cases':len(newread['cases']),'new_unique_inputs':len(new),'overlaps':overlap,'specs':new,'existing_receipts':inputs,'existing_case_counts':counts}
(P/'DEDUPLICATED-COMPOUND01.json').write_text(json.dumps(report,indent=2)+'\n');print({k:report[k]for k in ['existing_cases','existing_unique_inputs','new_executed_cases','new_unique_inputs']})
