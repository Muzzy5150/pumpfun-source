import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from pump_quote_control_function_match import sections
P=Path(__file__).resolve().parent;build=P/'build-direct-trait';audit=json.loads((build/'direct-dependency-audit.json').read_text());base=json.loads((ROOT/'work/parallel-main-create-handlers/build-v2-metadata-combined/build-comparison.json').read_text());cache=Path(base['dependency_cache']['cache_root'])/base['dependency_cache']['key']/'files'
def sha(b):return hashlib.sha256(b).hexdigest()
def ar(raw):
 assert raw[:8]==b'!<arch>\n';at=8;names=b'';out={}
 while at<len(raw):
  h=raw[at:at+60];assert h[58:60]==b'`\n';size=int(h[48:58]);name=h[:16].decode().strip();b=raw[at+60:at+60+size];at+=60+size+(size%2)
  if name=='//':names=b;continue
  if name.startswith('#1/'):
   n=int(name[3:]);name=b[:n].decode().rstrip('\0');b=b[n:]
  elif name.startswith('/')and name[1:].isdigit():name=names[int(name[1:]):].split(b'/\n')[0].decode()
  if name not in ['/','/SYM64/']:out[name.rstrip('/')]=b
 return out
def text(raw):
 if raw[:4]==b'\x7fELF':
  sec=sections(raw).get('.text');return None if sec is None else raw[sec['offset']:sec['offset']+sec['size']]
 if raw[:4]!=b'\xcf\xfa\xed\xfe':return None
 at=32;parts=[]
 for i in range(struct.unpack_from('<I',raw,16)[0]):
  cmd,size=struct.unpack_from('<II',raw,at)
  if cmd==0x19:
   n=struct.unpack_from('<I',raw,at+64)[0]
   for j in range(n):
    q=at+72+j*80;name=raw[q:q+16].rstrip(b'\0');length=struct.unpack_from('<Q',raw,q+40)[0];off=struct.unpack_from('<I',raw,q+48)[0]
    if name==b'__text':parts.append(raw[off:off+length])
  at+=size
 return b''.join(parts)if parts else None
rows=[]
for p in audit['external_compiled_payloads']:
 if p['actual_sha256']==p['baseline_sha256']or p['actual_sha256']is None:continue
 rel=p['path'];a=(cache/rel).read_bytes();b=(build/'target'/rel).read_bytes()
 if rel.endswith('.rlib'):
  am=ar(a);bm=ar(b)
  for name in sorted(set(am)&set(bm)):
   ta=text(am[name]);tb=text(bm[name])
   if ta is not None or tb is not None:rows.append({'path':rel,'member':name,'text_equal':ta==tb,'old_text_sha256':sha(ta)if ta is not None else None,'new_text_sha256':sha(tb)if tb is not None else None})
  if set(am)!=set(bm):rows.append({'path':rel,'member_name_difference':True,'old_only':sorted(set(am)-set(bm)),'new_only':sorted(set(bm)-set(am))})
 elif rel.endswith('.dylib'):
  ta=text(a);tb=text(b);rows.append({'path':rel,'text_equal':ta==tb,'old_text_sha256':sha(ta)if ta is not None else None,'new_text_sha256':sha(tb)if tb is not None else None})
out={'scope':'Machine-code section audit for changed external compiled payloads; metadata/other sections and container bytes are not claimed equal.','comparisons':rows,'text_compared':sum('text_equal'in x for x in rows),'text_differences':sum(x.get('text_equal')is False for x in rows),'member_name_differences':sum(x.get('member_name_difference',False)for x in rows)};(build/'external-text-audit.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items()if k!='comparisons'})
