import json,collections,sys
sys.path.insert(0,'tools'); import pm
o=json.load(open('origins-orig.json')); c=json.load(open(sys.argv[2] if len(sys.argv)>2 else 'origins-r20.json'))
inv=pm.read_json(pm.WT/'repro/pump/main-contract-round26-20261027/inventory.json.gz')
c2o={}
for w in inv['windows']:
  for m in w['normalized_matches']: c2o[m['start']]=w['start']
def line(r):
  ls=[x for x in r['stw_imms'] if x<2000]; cs=[x for x in r['stw_imms'] if x>=2000]
  return (ls[0] if ls else -1, cs[0] if cs else -1)
f=sys.argv[1]
print('ORIG',f)
for r in sorted(o,key=lambda r:line(r)):
  if r['file'].endswith(f): print('  ',line(r),hex(r['start']),r['tag'])
print('CAND',f)
for r in sorted(c,key=lambda r:line(r)):
  if r['file'].endswith(f): print('  ',line(r),hex(r['start']),'M'+hex(c2o[r['start']]) if r['start'] in c2o else 'U',r['tag'][-60:])
