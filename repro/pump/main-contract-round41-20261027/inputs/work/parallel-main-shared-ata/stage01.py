from pathlib import Path
import json,hashlib,shutil
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;B=R/'work/parallel-main-ata-drop/source02';S=W/'source01';assert not S.exists();shutil.copytree(B,S)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=S/'src/buy_v2.rs';s=p.read_text();start=s.index('  require!(a.associated_quote_bonding_curve.owner');end=s.index('\n }',start)
s=s[:start]+'''  admit_associated_token_account(a.associated_quote_bonding_curve.as_ref(),&a.bonding_curve.to_account_info(),&a.quote_mint.key(),&a.quote_token_program.key(),a.user.as_ref(),&a.quote_mint.to_account_info(),false,a.system_program.as_ref(),a.quote_token_program.as_ref())?;
  require_keys_eq!(*a.associated_quote_user.owner,a.quote_token_program.key(),PumpError::AccountTypeNotSupported);
  check_token(&a.associated_quote_user,a.quote_mint.key(),a.user.key())?;{let d=a.associated_quote_user.try_borrow_data()?;let t=TokenAccount::try_deserialize(&mut &d[..])?;require_keys_eq!(t.owner,a.user.key(),PumpError::AccountTypeNotSupported);}
  for (destination,authority) in [(a.associated_creator_vault.to_account_info(),a.creator_vault.to_account_info()),(a.associated_user_volume_accumulator.to_account_info(),a.user_volume_accumulator.to_account_info()),(a.associated_quote_fee_recipient.to_account_info(),a.fee_recipient.to_account_info()),(a.associated_quote_buyback_fee_recipient.to_account_info(),a.buyback_fee_recipient.to_account_info())]{
   admit_associated_token_account(&destination,&authority,&a.quote_mint.key(),&a.quote_token_program.key(),a.user.as_ref(),&a.quote_mint.to_account_info(),true,a.system_program.as_ref(),a.quote_token_program.as_ref())?;
  }'''+s[end:]
helper='''
// Shared main-program admission for an ATA, including the optional idempotent creation.
#[inline(never)]
pub fn admit_associated_token_account<'info>(account:&AccountInfo<'info>,authority:&AccountInfo<'info>,mint:&Pubkey,token_program:&Pubkey,payer:&AccountInfo<'info>,mint_info:&AccountInfo<'info>,allow_create:bool,system_program:&AccountInfo<'info>,token_program_info:&AccountInfo<'info>)->Result<()>{
 let expected=anchor_spl::associated_token::get_associated_token_address_with_program_id(&authority.key(),mint,token_program);
 require_keys_eq!(account.key(),expected,anchor_lang::error::ErrorCode::ConstraintSeeds);
 if account.owner==&anchor_lang::system_program::ID {
  require!(allow_create,anchor_lang::error::ErrorCode::AccountNotInitialized);
  let instruction=anchor_spl::associated_token::spl_associated_token_account::instruction::create_associated_token_account_idempotent(payer.key,authority.key,mint,token_program);
  let account_infos=[payer.clone(),account.clone(),authority.clone(),mint_info.clone(),system_program.clone(),token_program_info.clone()];
  anchor_lang::solana_program::program::invoke(&instruction,&account_infos)?;
 }
 require_keys_eq!(*account.owner,*token_program,PumpError::AccountTypeNotSupported);
 let data=account.try_borrow_data()?;
 let token=TokenAccount::try_deserialize_unchecked(&mut &data[..])?;
 require_keys_eq!(token.mint,*mint,PumpError::MintDoesNotMatchBondingCurve);
 Ok(())
}
'''
s+=helper;p.write_text(s)
p=S/'src/sell_v2.rs';s=p.read_text();start=s.index('  require!(a.associated_quote_bonding_curve.owner');end=s.index('\n }',start)
s=s[:start]+'''  crate::buy_v2::admit_associated_token_account(a.associated_quote_bonding_curve.as_ref(),&a.bonding_curve.to_account_info(),&a.quote_mint.key(),&a.quote_token_program.key(),a.user.as_ref(),&a.quote_mint.to_account_info(),false,a.system_program.as_ref(),a.quote_token_program.as_ref())?;
  require_keys_eq!(*a.associated_quote_user.owner,a.quote_token_program.key(),PumpError::AccountTypeNotSupported);
  check_token(&a.associated_quote_user,a.quote_mint.key(),a.user.key())?;{let d=a.associated_quote_user.try_borrow_data()?;let t=TokenAccount::try_deserialize(&mut &d[..])?;require_keys_eq!(t.owner,a.user.key(),PumpError::AccountTypeNotSupported);}
  for (destination,authority) in [(a.associated_creator_vault.to_account_info(),a.creator_vault.to_account_info()),(a.associated_user_volume_accumulator.to_account_info(),a.user_volume_accumulator.to_account_info()),(a.associated_quote_fee_recipient.to_account_info(),a.fee_recipient.to_account_info()),(a.associated_quote_buyback_fee_recipient.to_account_info(),a.buyback_fee_recipient.to_account_info())]{
   crate::buy_v2::admit_associated_token_account(&destination,&authority,&a.quote_mint.key(),&a.quote_token_program.key(),a.user.as_ref(),&a.quote_mint.to_account_info(),true,a.system_program.as_ref(),a.quote_token_program.as_ref())?;
  }'''+s[end:];p.write_text(s)
p=S/'src/sweep_fees.rs';s=p.read_text();start=s.index('  for (index,account)');end=s.index('\n  let mint=',start)
s=s[:start]+'''  crate::buy_v2::admit_associated_token_account(a.associated_quote_bonding_curve.as_ref(),&a.bonding_curve.to_account_info(),&a.quote_mint.key(),&a.quote_token_program.key(),a.payer.as_ref(),&a.quote_mint.to_account_info(),false,a.system_program.as_ref(),a.quote_token_program.as_ref())?;
  crate::buy_v2::admit_associated_token_account(a.associated_quote_recipient.as_ref(),a.recipient.as_ref(),&a.quote_mint.key(),&a.quote_token_program.key(),a.payer.as_ref(),&a.quote_mint.to_account_info(),true,a.system_program.as_ref(),a.quote_token_program.as_ref())?;'''+s[end:];p.write_text(s)
files=lambda d:{str(p.relative_to(d)):sha(p)for p in sorted(d.rglob('*'))if p.is_file()}
before,after=files(B),files(S);changed=[n for n in before if before[n]!=after[n]];assert changed==['src/buy_v2.rs','src/sell_v2.rs','src/sweep_fees.rs'];(W/'PLAN01.json').write_text(json.dumps({'baseline':str(B),'source':str(S),'baseline_sha256':before,'source_sha256':after,'changed':changed,'hypothesis':'Recover original shared ATA address, selected owner, optional creation and mint admission in original order; genuine six-info idempotent ATA instruction via invoke.'},indent=2)+'\n');print(changed)
