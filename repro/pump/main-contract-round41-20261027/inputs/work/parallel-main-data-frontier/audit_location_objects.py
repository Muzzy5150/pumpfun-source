"""Decode candidate Rust source-location objects through captured ELF relocations.

Shape recognition and paired normalized bodies are triage evidence, not proof of object identity.
"""
from pathlib import Path
import argparse,collections,hashlib,json,struct,sys
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
from pump_quote_control_function_match import sections
parser=argparse.ArgumentParser();parser.add_argument('--frontier',type=Path,default=W/'round23-frontier.json');parser.add_argument('--candidate',type=Path,default=R/'work/parallel-main-integration/build-round23-final/unstripped.so');parser.add_argument('--output',type=Path,default=W/'round23-location-objects.json');args=parser.parse_args()
D=json.loads(args.frontier.read_text())
ob=(R/'evidence/original/pump/deployed.so').read_bytes();cb=args.candidate.read_bytes()
assert hashlib.sha256(ob).hexdigest()==D['original_sha256']
assert hashlib.sha256(cb).hexdigest()==D['candidate_sha256']
def read(b,ss,a,n):
 for s in ss.values():
  if s['addr'] and s['addr']<=a and a+n<=s['addr']+s['size']:
   offset=s['offset']+a-s['addr'];return b[offset:offset+n]
 return b''
def relocations(b,ss):
 out={};s=ss['.rel.dyn']
 for at in range(s['offset'],s['offset']+s['size'],16):
  address,kind=struct.unpack_from('<QQ',b,at)
  if kind!=8:continue
  raw=read(b,ss,address,8)
  if len(raw)!=8:continue
  low,high=struct.unpack('<II',raw)
  if low==0:out[address]=high
 return out
def location(b,ss,rel,a):
 raw=read(b,ss,a,24)
 if len(raw)!=24 or a not in rel:return None
 _,length,line,column=struct.unpack('<QQII',raw)
 if not 1<=length<=512 or not 1<=line<=1000000 or not 1<=column<=100000:return None
 path=read(b,ss,rel[a],length)
 try:path=path.decode('utf-8')
 except UnicodeDecodeError:return None
 if not path.endswith('.rs') or '\0' in path:return None
 return {'file':path,'line':line,'column':column,'length':length,'pointer':hex(rel[a])}
os=sections(ob);cs=sections(cb);orr=relocations(ob,os);cr=relocations(cb,cs)
rows=[];counts=collections.Counter()
for row in D['unambiguous_data_prefixes']:
 if row['original_section']!='.data.rel.ro' or row['candidate_section']!='.data.rel.ro':continue
 a=location(ob,os,orr,int(row['original'],16));b=location(cb,cs,cr,int(row['candidate'],16))
 if a is None or b is None:continue
 counts['shape_recognized_pairs']+=1;counts['same_filename']+=a['file']==b['file'];counts['same_filename_line_column']+=all(a[k]==b[k]for k in ['file','line','column'])
 rows.append({'original_address':row['original'],'candidate_address':row['candidate'],'original':a,'candidate':b,'uses':row['uses']})
result={'scope':__doc__,'original_sha256':D['original_sha256'],'candidate_sha256':D['candidate_sha256'],'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'counts':dict(counts),'pairs':rows,'full_data_identity':False,'goal_complete':False}
args.output.write_text(json.dumps(result,indent=2)+'\n');print(counts)
