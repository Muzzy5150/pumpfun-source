use anchor_lang::prelude::*;
use crate::CollectCreatorFeeEvent;
#[event_cpi]
#[derive(Accounts)]
pub struct CollectCreatorFeeV2<'info>{
 /// CHECK: recipient only tied to vault/ATA seeds.
 #[account(mut)]pub creator:AccountInfo<'info>,
 /// CHECK: token program validates data only during positive token transfer.
 #[account(mut,seeds=[creator.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=associated_token_program.key())]pub creator_token_account:UncheckedAccount<'info>,
 /// CHECK: address constrained, native transfer defers owner/data checks.
 #[account(mut,seeds=[b"creator-vault",creator.key().as_ref()],bump)]pub creator_vault:AccountInfo<'info>,
 /// CHECK: address constrained, token program validates on transfer.
 #[account(mut,seeds=[creator_vault.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=associated_token_program.key())]pub creator_vault_token_account:UncheckedAccount<'info>,
 pub quote_mint:Box<InterfaceAccount<'info,anchor_spl::token_interface::Mint>>,
 pub quote_token_program:Interface<'info,anchor_spl::token_interface::TokenInterface>,
 pub associated_token_program:Program<'info,anchor_spl::associated_token::AssociatedToken>,
 pub system_program:Program<'info,System>,
}
pub fn collect<'info>(
 creator:&AccountInfo<'info>,creator_token_account:&AccountInfo<'info>,creator_vault:&AccountInfo<'info>,
 creator_vault_bump:u8,creator_vault_token_account:&AccountInfo<'info>,decimals:u8,quote_mint:&AccountInfo<'info>,
 quote_token_program:&Interface<'info,anchor_spl::token_interface::TokenInterface>,system_program:&AccountInfo<'info>,
)->Result<Option<(u64,Pubkey)>>{
 require!(*creator.owner!=crate::distribution::FEES,crate::PumpError::UnableToDistributeCreatorVaultMigratedToSharingConfig);
 if creator.executable{msg!("Creator account is executable, so it cannot receive lamports");return Ok(None);}
 let native=quote_mint.key()==anchor_spl::token::spl_token::native_mint::ID;
 let amount=if native{
  let rent=Rent::get()?;
  let amount=creator_vault.lamports().saturating_sub(rent.minimum_balance(0));
  if amount>0 && creator.lamports().saturating_add(amount)<rent.minimum_balance(creator.data_len()){msg!("Creator account does not have enough rent-exemption lamports");return Ok(None);}
  amount
 }else{
  let data=creator_vault_token_account.try_borrow_data()?;anchor_spl::token_interface::TokenAccount::try_deserialize(&mut &data[..])?.amount
 };
 if amount==0{msg!("No creator fee to collect");return Ok(None);}
 let creator_key=creator.key();let bump=[creator_vault_bump];let seeds:&[&[u8]]=&[b"creator-vault",creator_key.as_ref(),&bump];
 if native{anchor_lang::system_program::transfer(CpiContext::new_with_signer(system_program.to_account_info(),anchor_lang::system_program::Transfer{from:creator_vault.clone(),to:creator.clone()},&[seeds]),amount)?;}
 else{anchor_spl::token_interface::transfer_checked(CpiContext::new_with_signer(quote_token_program.to_account_info(),anchor_spl::token_interface::TransferChecked{from:creator_vault_token_account.clone(),mint:quote_mint.clone(),to:creator_token_account.clone(),authority:creator_vault.clone()},&[seeds]),amount,decimals)?;}
 Ok(Some((amount,if native{Pubkey::default()}else{quote_mint.key()})))
}

pub fn execute(ctx:Context<CollectCreatorFeeV2>)->Result<()>{
 let a=&ctx.accounts;
 if let Some((amount,quote_mint))=collect(&a.creator,a.creator_token_account.as_ref(),&a.creator_vault,ctx.bumps.creator_vault,a.creator_vault_token_account.as_ref(),a.quote_mint.decimals,a.quote_mint.as_ref().as_ref(),&a.quote_token_program,a.system_program.as_ref())?{
  let event=CollectCreatorFeeEvent{timestamp:Clock::get()?.unix_timestamp,creator:a.creator.key(),creator_fee:amount,quote_mint};emit!(event);emit_cpi!(event);
 }
 Ok(())
}
