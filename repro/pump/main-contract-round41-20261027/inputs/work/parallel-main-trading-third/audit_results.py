"""Audit real paired diagnostics; excludes source coordinates and compute units."""
from pathlib import Path
import argparse, gzip, json, re, collections
W=Path(__file__).resolve().parent

def messages(xs):
    panic=[];anchor=[];compared=[];origins=[];pending=None
    for x in xs:
        if x.startswith('Program log: Left:') or x.startswith('Program log: Right:'):
            side=x.split('Program log: ',1)[1].split(':',1)[0];value=x.split(':',2)[2].strip()
            if value:compared.append([side,value]);pending=None
            else:pending=side
        elif pending is not None and x.startswith('Program log: '):
            compared.append([pending,x.removeprefix('Program log: ')]);pending=None
        else:pending=None
        if 'panicked at ' in x:panic.append(x.split('\n',1)[1] if '\n' in x else x)
        if 'AnchorError' in x:
            origin=re.search(r'AnchorError caused by account: (.*?)\. Error Code:',x)
            origins.append(['account',origin.group(1)] if origin else ['source'] if 'AnchorError thrown in ' in x else ['none'])
            m=re.search(r'Error Code: (.*?)\. Error Number: (\d+)\. Error Message: (.*)',x);anchor.append(m.groups() if m else x)
    return {'panic':panic,'anchor':anchor,'compared':compared,'origins':origins}

def main():
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();rows=[];coverage=collections.Counter()
 def walk(value,path):
  if isinstance(value,dict):
   if isinstance(value.get('original'),dict) and isinstance(value.get('candidate'),dict):
    o=value['original'];c=value['candidate'];ol=o.get('logs',[]);cl=c.get('logs',[])
    if ol or cl:
     coverage[path.split('/')[0]]+=1;x,y=messages(ol),messages(cl)
     if x!=y:rows.append({'path':path,'case':value.get('case',value.get('name')),'original':x,'candidate':y})
   for k,v in value.items():
    if k not in ('original','candidate'):walk(v,path+'/'+k)
  elif isinstance(value,list):
   for i,v in enumerate(value):walk(v,path+'/'+str(i))
 for path in sorted(a.directory.glob('*.json.gz')):
  b=path.read_bytes();d=json.loads(gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b);walk(d,path.stem.removesuffix('.json'))
 out={'coverage':dict(coverage),'mismatches':rows};(a.directory/'diagnostic-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(sum(coverage.values()),len(rows));print(collections.Counter(r['path'].split('/')[0] for r in rows))
if __name__=='__main__':main()
