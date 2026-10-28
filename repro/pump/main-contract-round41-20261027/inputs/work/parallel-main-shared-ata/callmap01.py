from pathlib import Path
import sys,json
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'))
from pump_compare_function_bytes import candidate_functions
funcs=candidate_functions(W/'build01/unstripped.so',str(R/'work/fees-compat/toolchains/v1.44/llvm/bin/llvm-objdump'),'.')
cf={a:(n,s)for a,s,n in funcs};iv=json.loads((W/'build01/normalized-inventory.json').read_text());orig={}
for row in iv['windows']:
 if row['normalized_matches']:
  x=row['normalized_matches'][0];orig[row['start']]=x
j=json.loads((W/'helper01.json').read_text());rows=[]
for side,ops in [('original',j['original_operands']),('candidate',j['candidates'][0]['operands'])]:
 out=[]
 for op in ops:
  if op['kind']!='direct-call':continue
  target=op['target'];m=orig.get(target);name=cf.get(target)if side=='candidate'else m
  out.append({'offset':hex(op['offset']),'target':hex(target),'name':name})
 rows.append({'side':side,'calls':out})
(W/'CALLS01.json').write_text(json.dumps(rows,indent=2)+'\n')
for side in rows:
 print(side['side'])
 for row in side['calls']:print(row)
