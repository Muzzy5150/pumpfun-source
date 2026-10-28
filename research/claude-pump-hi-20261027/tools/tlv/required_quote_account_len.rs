#[inline(never)]
pub fn required_quote_account_len(data:&[u8])->Option<usize>{
 let mut size=170usize;
 if data.len()==82{return Some(size)}
 if data.len()<167 || data[82..165].iter().any(|byte|*byte!=0) || data[165]!=1{return None}
 let tlv=&data[166..];
 let mut cursor=0usize;let mut seen=0u64;
 loop{
  let rest=tlv.get(cursor..)?;
  if rest.len()<2{return Some(size)}
  let kind=u16::from_le_bytes(rest[..2].try_into().unwrap());
  if kind==0{return Some(size)}
  if rest.len()<4{return None}
  let end=u16::from_le_bytes(rest[2..4].try_into().unwrap()) as usize+4;
  if end>rest.len(){return None}
  if let Some(payload)=match kind {1=>Some(8usize),9=>Some(0),14=>Some(1),26=>Some(0),_=>None}{
   let mask=1u64<<kind;
   if seen&mask==0{size=size.checked_add(4)?.checked_add(payload)?;seen|=mask;}}
  cursor=cursor.checked_add(end)?;
 }
}
