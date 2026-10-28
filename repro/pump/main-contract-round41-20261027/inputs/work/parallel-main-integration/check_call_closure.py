"""Prune normalized body matches unless every masked direct call has a matching body pair.

ELF-pointer operands are excluded (their referenced objects are not recovered).
This proves a static body/call relationship, not behavioral or whole-ELF equality.
"""
from pathlib import Path
import json,collections,argparse
w=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
r=json.loads(args.inventory.read_text())
rows={x['start']:x for x in r['windows']}; active={};excluded=collections.Counter()
for a,row in rows.items():
 for m in row['normalized_matches']:
  oo=row['original_operands'];co=m['operands']
  if [(x['offset'],x['kind']) for x in oo] != [(x['offset'],x['kind']) for x in co]:
   excluded['different_operand_kinds']+=1;continue
  if any(x['kind']=='elf-pointer' for x in oo):
   excluded['unresolved_data_reference']+=1;continue
  active[(a,m['start'])]={'original_start':a,'candidate_start':m['start'],'bytes':row['bytes'],'candidate_symbol':m['symbol'],'raw_equal':row['raw_sha256']==m['raw_sha256'],'calls':[{'offset':x['offset'],'original_target':x['target'],'candidate_target':y['target']} for x,y in zip(oo,co)]}
iterations=[]
while True:
 dead={p for p,m in active.items() if any((c['original_target'],c['candidate_target']) not in active for c in m['calls'])}
 if not dead:break
 iterations.append(len(dead))
 for p in dead:del active[p]
unique={a for a,b in active};out={'scope':__doc__,'original_sha256':r['original_sha256'],'candidate_sha256':r['candidate_sha256'],'counts':{'original_windows':len(rows),'normalized_windows':r['counts']['normalized'],'closed_call_graph_windows_without_data_references':len(unique),'pairs':len(active)},'initial_exclusions':dict(excluded),'pruning_rounds':iterations,'pairs':list(active.values())}
args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['counts']));print('pruning',iterations)
