from pathlib import Path
import json,hashlib,shutil
W=Path(__file__).resolve().parent;B=W/'source02';S=W/'source04';assert not S.exists();shutil.copytree(B,S);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in ['buy_v2.rs','sell_v2.rs','sweep_fees.rs']:
 p=S/'src'/n;s=p.read_text()
 for payer in ['user','payer']:
  for flag in ['false','true']:
   a=f'a.{payer}.as_ref(),&a.quote_mint.to_account_info(),{flag},a.system_program.as_ref()'
   b=f'a.system_program.as_ref(),&a.quote_mint.to_account_info(),{flag},a.{payer}.as_ref()';s=s.replace(a,b)
 if n=='buy_v2.rs':
  a="payer:&AccountInfo<'info>,mint_info:&AccountInfo<'info>,allow_create:bool,system_program:&AccountInfo<'info>";b="system_program:&AccountInfo<'info>,mint_info:&AccountInfo<'info>,allow_create:bool,payer:&AccountInfo<'info>";assert s.count(a)==1;s=s.replace(a,b)
 p.write_text(s)
(W/'PLAN04.json').write_text(json.dumps({'baseline':str(B),'source':str(S),'change':'Original builder obtains payer key and first clone from stack -0xfe0, and system fifth clone from stack -0xff8. Swap only these two parameter positions and their call arguments, keeping semantic bindings unchanged.','corrected_order':['account','authority','mint key','token key','system info','mint info','allow_create','payer info','token info'],'before':{n:sha(B/'src'/n)for n in ['buy_v2.rs','sell_v2.rs','sweep_fees.rs']},'after':{n:sha(S/'src'/n)for n in ['buy_v2.rs','sell_v2.rs','sweep_fees.rs']}},indent=2)+'\n')
