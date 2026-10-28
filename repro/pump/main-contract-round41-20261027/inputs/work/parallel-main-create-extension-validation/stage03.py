from pathlib import Path
import shutil,hashlib,json
out=Path(__file__).resolve().parent;src=out/'source03';assert not src.exists();shutil.copytree(out/'source02',src);p=src/'src/create_v2.rs';s=p.read_text();a=s.index('pub fn quote_extensions_supported');b=s.index('\n}\n',a)+3
body='''pub fn quote_extensions_supported(data:&[u8],allow_token_extensions:bool)->bool {
 if data.len()==82{return true;}
 if data.len()<167 || data[82..165].iter().any(|&b|b!=0) || data[165]!=1{return false;}
 let data=&data[166..];
 let mut seen=0u64;
 let mut at=0usize;
 while let Some(entry)=data.get(at..){
  if entry.len()<2{return true;}
  let kind=u16::from_le_bytes(entry[..2].try_into().unwrap());
  if kind==0{return true;}
  if entry.len()<4{return false;}
  let size=u16::from_le_bytes(entry[2..4].try_into().unwrap()) as usize;
  let entry_size=4+size;
  if entry_size>entry.len(){return false;}
  match kind{
   18|19=>{},
   1|4|6|12|14|16|25|26=>if !allow_token_extensions{return false;},
   _=>return false,
  }
  let bit=1u64<<kind;
  if seen&bit!=0{return false;}
  let bytes=&entry[4..entry_size];
  match kind{
   1=>if bytes.len()<108{return false;},
   6=>if bytes.is_empty() || bytes[0]!=1{return false;},
   14=>if bytes.len()<64 || bytes[32..64]!=[0;32]{return false;},
   _=>{},
  }
  seen|=bit;
  at=match at.checked_add(entry_size){Some(next)=>next,None=>return false};
 }
 false
}
'''
p.write_text(s[:a]+body+s[b:]);(out/'PLAN03.json').write_text(json.dumps({'source':str(src),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'change':'Use bounded remaining TLV slice each iteration; decode constant two-byte ranges after their checks; advance checked relative index at loop end. Original uses one base pointer/length, remaining slice, native16-bit header loads and end-of-loop checked advance, with no panicking index calls.'},indent=2)+'\n');print(hashlib.sha256(p.read_bytes()).hexdigest())
