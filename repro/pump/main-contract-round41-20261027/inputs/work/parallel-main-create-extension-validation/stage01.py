from pathlib import Path
import shutil,hashlib,json
r=Path.cwd();out=r/'work/parallel-main-create-extension-validation';base=r/'work/parallel-main-integration/round24-final-source/programs/pump';source=out/'source01';assert not source.exists();shutil.copytree(base,source)
p=source/'src/create_v2.rs';s=p.read_text();assert s.count('quote_extensions_supported(&mint.try_borrow_data()?)')==1;s=s.replace('quote_extensions_supported(&mint.try_borrow_data()?)','quote_extensions_supported(&mint.try_borrow_data()?,true)')
a=s.index('fn quote_extensions_supported(');b=s.index('\n}\n',a)+3
s=s[:a]+'''#[inline(never)]
pub fn quote_extensions_supported(data:&[u8],allow_token_extensions:bool)->bool {
 if data.len()==82{return true;}
 if data.len()<167 || data[82..165].iter().any(|&b|b!=0) || data[165]!=1{return false;}
 let mut seen=0u64;
 let mut at=166usize;
 while at<data.len(){
  let remaining=data.len()-at;
  if remaining<2{return true;}
  let kind=u16::from_le_bytes([data[at],data[at+1]]);
  if kind==0{return true;}
  if remaining<4{return false;}
  let size=u16::from_le_bytes([data[at+2],data[at+3]]) as usize;
  let next=match at.checked_add(4+size){Some(next) if next<=data.len()=>next,_=>return false};
  match kind{
   18|19=>{},
   1|4|6|12|14|16|25|26=>if !allow_token_extensions{return false;},
   _=>return false,
  }
  let bit=1u64<<kind;
  if seen&bit!=0{return false;}
  let bytes=&data[at+4..next];
  match kind{
   1=>if bytes.len()<108{return false;},
   6=>if bytes.is_empty() || bytes[0]!=1{return false;},
   14=>if bytes.len()<64 || bytes[32..64]!=[0;32]{return false;},
   _=>{},
  }
  seen|=bit;
  at=next;
 }
 true
}
'''+s[b:];p.write_text(s)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();files=lambda d:{str(p.relative_to(d)):sha(p) for p in sorted(d.rglob('*')) if p.is_file()};a,b=files(base),files(source);assert [k for k in a if a[k]!=b[k]]==['src/create_v2.rs'];(out/'PLAN01.json').write_text(json.dumps({'baseline':str(base),'source':str(source),'source_files':b,'baseline_files':a,'change':'Restore main-owned quote extension validator padding,duplicate-kind,partial-tail rules and observed dynamic bool ABI. Existing allowed kind payload checks preserved.','original_start':'0x17bc48','original_bytes':1192,'before_cases':26,'before_mismatches':19},indent=2)+'\n');print(sha(p))
