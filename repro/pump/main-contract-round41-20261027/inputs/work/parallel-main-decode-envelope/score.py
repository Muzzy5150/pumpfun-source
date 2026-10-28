from pathlib import Path
import csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from pump_compare_function_bytes import body,normalize
from pump_quote_control_function_match import sections,candidate_functions
build=Path(sys.argv[1]);candidate=build/'unstripped.so';original=ROOT/'evidence/original/pump/deployed.so';ob=original.read_bytes();cb=candidate.read_bytes();os=sections(ob);cs=sections(cb);sha=lambda b:hashlib.sha256(b).hexdigest()
funcs=candidate_functions(candidate,str(ROOT/'work/fees-compat/toolchains/v1.44/llvm/bin/llvm-objdump'),'.')
windows={int(r['original_start']):int(r['original_end'])-int(r['original_start'])for r in csv.DictReader((ROOT/'repro/reconstruction-status-2026-10-26/functions.tsv').open(),delimiter='\t')if r['program']=='pump'and r['variant']=='selected'}
checks=[('checked',0x9b148,lambda n:'trade_types..BondingCurve' in n and '$GT$15try_deserialize17h'in n),('unchecked',0x9b430,lambda n:'trade_types..BondingCurve' in n and '$GT$25try_deserialize_unchecked17h'in n)]
leaf=[0x9b6a0,0x9bc28,0x9c240,0x9c8f8,0x9d008,0x9d850,0x9e178,0x9eaf0,0x9f500]
for i,a in enumerate(leaf):checks.append((f'v{i}',a,lambda n,i=i:f'historical_curve9decode_v{i}17h'in n))
rows=[]
for label,a,pred in checks:
 n=windows[a];o=body(ob,os,a,n);on,oo=normalize(o,a,os);matches=[]
 for start,size,name in funcs:
  if not pred(name):continue
  b=body(cb,cs,start,size);bn,bo=normalize(b,start,cs);diff=[{'offset':i,'original':on[i:i+8].hex(),'candidate':bn[i:i+8].hex()}for i in range(0,max(len(on),len(bn)),8)if on[i:i+8]!=bn[i:i+8]]
  prefix=next((i for i in range(0,min(len(on),len(bn)),8)if on[i:i+8]!=bn[i:i+8]),min(len(on),len(bn)))
  matches.append({'start':hex(start),'bytes':size,'symbol':name,'normalized_equal':on==bn,'raw_equal':o==b,'equal_prefix_bytes':prefix,'different_slots':diff,'operands':bo})
 rows.append({'label':label,'original_start':hex(a),'original_bytes':n,'original_operands':oo,'candidates':matches})
r={'original_sha256':sha(ob),'candidate_sha256':sha(cb),'checks':rows,'all_nine_exact':all(any(c['normalized_equal']for c in row['candidates'])for row in rows[2:])}
(build/'envelope-comparison.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'build':str(build),'all_nine_exact':r['all_nine_exact'],'envelopes':[{k:x[k]for k in ['label','original_bytes']}|{'candidates':[{k:c[k]for k in ['start','bytes','normalized_equal','equal_prefix_bytes']}|{'different_slots':len(c['different_slots'])}for c in x['candidates']]}for x in rows[:2]]}))
