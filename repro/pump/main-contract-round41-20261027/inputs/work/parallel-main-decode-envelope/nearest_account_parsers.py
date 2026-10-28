from pathlib import Path
import csv,difflib,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from pump_compare_function_bytes import normalize,body
from pump_quote_control_function_match import sections,candidate_functions
ob=(ROOT/'evidence/original/pump/deployed.so').read_bytes();cpath=ROOT/'work/parallel-main-integration/build-round14/unstripped.so';cb=cpath.read_bytes();os=sections(ob);cs=sections(cb)
orig=[]
for r in csv.DictReader((ROOT/'repro/reconstruction-status-2026-10-26/functions.tsv').open(),delimiter='\t'):
 if r['program']!='pump'or r['variant']!='selected':continue
 a=int(r['original_start']);n=int(r['bytes']);b,_=normalize(body(ob,os,a,n),a,os);orig.append((a,n,[b[i:i+8]for i in range(0,n,8)]))
rows=[]
for a,n,name in candidate_functions(cpath,str(ROOT/'work/fees-compat/toolchains/v1.44/llvm/bin/llvm-objdump'),'AccountDeserialize'):
 if not any(key in name for key in ['..Global$','GlobalVolumeAccumulator','UserVolumeAccumulator','SharingConfig','RouteFeeConfig','LegacyFeeConfig']):continue
 b,_=normalize(body(cb,cs,a,n),a,cs);c=[b[i:i+8]for i in range(0,n,8)];scores=[]
 for oa,on,o in orig:
  if abs(on-n)>32:continue
  equal=sum(x==y for x,y in zip(c,o));same=sum(bl.size for bl in difflib.SequenceMatcher(None,c,o,autojunk=False).get_matching_blocks());scores.append({'original':hex(oa),'bytes':on,'positional_equal':equal,'sequence_equal':same,'candidate_slots':len(c)})
 scores.sort(key=lambda x:(-x['sequence_equal'],abs(n-x['bytes'])))
 rows.append({'candidate':hex(a),'bytes':n,'symbol':name,'nearest':scores[:3]})
(ROOT/'work/parallel-main-decode-envelope/nearest-parsers.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
