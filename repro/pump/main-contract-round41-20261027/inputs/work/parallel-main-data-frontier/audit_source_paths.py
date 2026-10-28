"""Measure filename agreement in paired main-Pump diagnostics; no line masking claims."""
from pathlib import Path
import argparse, collections, gzip, hashlib, json, re
PATTERN=re.compile(r'(programs/pump/src/[A-Za-z0-9_./-]+\.rs):(\d+)(?::(\d+))?')
def read(path):
 data=path.read_bytes();return json.loads(gzip.decompress(data)if data[:2]==b'\x1f\x8b'else data)
def measure(report):
 counts=collections.Counter();pairs=collections.Counter()
 def walk(value):
  if isinstance(value,dict):
   if isinstance(value.get('original'),dict)and isinstance(value.get('candidate'),dict):
    left=value['original'];right=value['candidate']
    for a,b in zip(left.get('logs',[]),right.get('logs',[])):
     aa=list(PATTERN.finditer(a));bb=list(PATTERN.finditer(b))
     if len(aa)==len(bb)==1 and PATTERN.sub('<SOURCE>',a)==PATTERN.sub('<SOURCE>',b):
      aa=aa[0];bb=bb[0];counts['paired_source_messages']+=1
      counts['equal_filename']+=aa.group(1)==bb.group(1)
      counts['equal_complete_location']+=aa.group()==bb.group()
      pairs[(aa.group(1),bb.group(1))]+=1
   for key,item in value.items():
    if key not in ['original','candidate']:walk(item)
  elif isinstance(value,list):
   for item in value:walk(item)
 walk(report['suites'])
 return {'counts':dict(counts),'path_pairs':[{'original':a,'candidate':b,'count':n}for(a,b),n in pairs.most_common()]}
def main():
 p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 old=read(a.before);new=read(a.after);assert old['case_count']==new['case_count']==10468
 before=measure(old);after=measure(new)
 assert after['counts'].get('equal_filename',0)>=before['counts'].get('equal_filename',0)
 result={'scope':__doc__,'before_sha256':hashlib.sha256(a.before.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(a.after.read_bytes()).hexdigest(),'before':before,'after':after,'whole_elf_equal':False}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print({'before':before['counts'],'after':after['counts']})
if __name__=='__main__':main()
