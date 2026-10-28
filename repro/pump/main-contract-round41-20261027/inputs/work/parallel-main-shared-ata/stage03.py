from pathlib import Path
import json,hashlib,shutil
W=Path(__file__).resolve().parent;B=W/'source02';S=W/'source03';assert not S.exists();shutil.copytree(B,S);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['buy_v2.rs','sell_v2.rs','sweep_fees.rs']:
 p=S/'src'/name;lines=p.read_text().splitlines(True)
 for i,line in enumerate(lines):
  if 'admit_associated_token_account(' in line and "pub fn" not in line:
   lines[i]=line.replace('&a.quote_mint.key(),&a.quote_token_program.key(),','a.quote_mint.key(),a.quote_token_program.key(),')
 s=''.join(lines)
 if name=='buy_v2.rs':
  old='mint:&Pubkey,token_program:&Pubkey';assert s.count(old)==1;s=s.replace(old,'mint:Pubkey,token_program:Pubkey');s=s.replace('(&authority.key(),mint,token_program)','(&authority.key(),&mint,&token_program)').replace('(&payer.key(),&authority.key(),mint,token_program)','(&payer.key(),&authority.key(),&mint,&token_program)').replace('require_keys_eq!(*account.owner,*token_program,','require_keys_eq!(*account.owner,token_program,').replace('require_keys_eq!(token.mint,*mint,','require_keys_eq!(token.mint,mint,')
 p.write_text(s)
(W/'PLAN03.json').write_text(json.dumps({'baseline':str(B),'source':str(S),'hypothesis':'Both key inputs originate as owned Key::key() values in original callers. Test owned Pubkey parameters versus borrowed Pubkey while keeping the genuine key copies for instruction construction, all guards and account-info layout. Original input ABI is indirect32-byte in either form; ownership remains a hypothesis.','before':{n:sha(B/'src'/n)for n in ['buy_v2.rs','sell_v2.rs','sweep_fees.rs']},'after':{n:sha(S/'src'/n)for n in ['buy_v2.rs','sell_v2.rs','sweep_fees.rs']}},indent=2)+'\n')
