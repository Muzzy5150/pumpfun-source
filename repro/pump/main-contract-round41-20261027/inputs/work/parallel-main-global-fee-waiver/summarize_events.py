from pathlib import Path
import json,gzip,base64
R=Path(__file__).resolve().parents[2];p=Path(__file__).parent;idl=json.load(open(R/'evidence/upstream/pump.json'));fields=next(x['type']['fields']for x in idl['types']if x['name']=='TradeEvent');disc=bytes(next(x['discriminator']for x in idl['events']if x['name']=='TradeEvent'))
def decode(r):
 for e in r.get('events',r.get('event_payloads',[])):
  b=base64.b64decode(e)
  if b[:8]!=disc:continue
  at=8;x={}
  for f in fields:
   t=f['type'];n=32 if t=='pubkey' else 1 if t=='bool' else int(t[1:])//8 if isinstance(t,str)and t[0] in 'ui' else None
   if n is None:break
   v=b[at:at+n];at+=n;x[f['name']]=v.hex() if t=='pubkey' else int.from_bytes(v,'little',signed=t.startswith('i'))
  return {k:x.get(k)for k in ['fee_basis_points','fee','creator_fee_basis_points','creator_fee','cashback_fee_basis_points','cashback','buyback_fee_basis_points','buyback_fee','holder_rewards_bps','holder_rewards']}
 return None
out=[]
for name in ['paired.json.gz','v3.json.gz']:
 if not (p/name).exists():continue
 r=json.load(gzip.open(p/name,'rt'))
 for row in r['cases']:
  out.append({'case':row['case']['name'],'route':row['route'],'mode':row['mode'],'original_error':row['original']['error'],'candidate_error':row['candidate']['error'],'original_event':decode(row['original']),'candidate_event':decode(row['candidate']),'different_fields':row['different_fields']})
(p/'EVENT-SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n')
for r in out:
 if r['mode']=='whitelist_user':print(json.dumps(r))
