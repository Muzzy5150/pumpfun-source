from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from pump_compare_function_bytes import body,normalize
from pump_quote_control_function_match import sections
r=json.loads((ROOT/'work/parallel-main-create-context/build-metadata-program/function-comparison.json').read_bytes());row=next(x for x in r['functions']if x['label']=='create_parser')
for label,p,a,n in [('original',ROOT/'evidence/original/pump/deployed.so',0x167528,11960),('candidate',ROOT/'work/parallel-main-create-context/build-metadata-program/unstripped.so',int(row['candidate']['start'],16),row['candidate']['bytes'])]:
 b=p.read_bytes();ss=sections(b);raw=body(b,ss,a,n);_,ops=normalize(raw,a,ss);print(label,hex(a),n)
 for op in ops:
  if op['kind']!='elf-pointer':continue
  v=op['value'];sec=next((s for k,s in ss.items()if k=='.rodata'and s['addr']<=v<s['addr']+s['size']),None)
  if not sec:continue
  off=v-sec['addr']+sec['offset'];value=b[off:off+42]
  try:text=value.decode('ascii')
  except UnicodeDecodeError:continue
  if not text[:1].isalpha():continue
  print(hex(op['offset']),repr(text))
