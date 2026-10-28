from pathlib import Path
import json,hashlib,shutil
W=Path(__file__).resolve().parent;B=W/'source02';S=W/'source06';assert not S.exists();shutil.copytree(B,S);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in ['buy_v2.rs','sell_v2.rs','sweep_fees.rs']:
 p=S/'src'/n;s=p.read_text()
 for payer in ['user','payer']:
  for flag in ['false','true']:
   a=f'a.{payer}.as_ref(),&a.quote_mint.to_account_info(),{flag},a.system_program.as_ref(),a.quote_token_program.as_ref()'
   b=f'&a.quote_mint.to_account_info(),a.quote_token_program.as_ref(),{flag},a.{payer}.as_ref(),a.system_program.as_ref()';s=s.replace(a,b)
 if n=='buy_v2.rs':
  a="payer:&AccountInfo<'info>,mint_info:&AccountInfo<'info>,allow_create:bool,system_program:&AccountInfo<'info>,token_program_info:&AccountInfo<'info>"
  b="mint_info:&AccountInfo<'info>,token_program_info:&AccountInfo<'info>,allow_create:bool,payer:&AccountInfo<'info>,system_program:&AccountInfo<'info>";assert s.count(a)==1;s=s.replace(a,b)
 p.write_text(s)
(W/'PLAN06.json').write_text(json.dumps({'baseline':str(B),'source':str(S),'change':'Original Sweep caller + exact parser layout and SDK type-size probe identify trailing arguments: mint info, token info, allow, payer info, system info. Preserve original standard payer/ATA/authority/mint/system/token info array.','before':{n:sha(B/'src'/n)for n in ['buy_v2.rs','sell_v2.rs','sweep_fees.rs']},'after':{n:sha(S/'src'/n)for n in ['buy_v2.rs','sell_v2.rs','sweep_fees.rs']}},indent=2)+'\n')
