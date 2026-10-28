use anchor_lang::prelude::*;
use crate::{AdminReadonly,AdminGlobal,PumpError,ReservedFeeRecipientsEvent};

pub fn execute(ctx:Context<AdminReadonly>,whitelist_pda:Pubkey)->Result<()>{
     require_gte!(ctx.remaining_accounts.len(),8,PumpError::NotEnoughRemainingAccounts);
     for (index,account) in ctx.remaining_accounts.iter().take(8).enumerate(){require_keys_neq!(account.key(),Pubkey::default(),PumpError::AllFeeRecipientsShouldBeNonZero);if account.executable{return Err(crate::account_name::with_owned_name(error!(anchor_lang::error::ErrorCode::ConstraintExecutable), &format!("reserved_fee_recipients[{}]",index)));}if !Rent::get()?.is_exempt(account.lamports(),account.data_len()){return Err(error!(anchor_lang::error::ErrorCode::ConstraintRentExempt).with_account_name(format!("reserved_fee_recipients[{}]",index)));}}
     let first=ctx.remaining_accounts[0].key();let rest=core::array::from_fn(|i|ctx.remaining_accounts[i+1].key());
     ctx.accounts.global.whitelist_pda=whitelist_pda;ctx.accounts.global.reserved_fee_recipient=first;ctx.accounts.global.reserved_fee_recipients=rest;
     let event=ReservedFeeRecipientsEvent{timestamp:Clock::get()?.unix_timestamp,reserved_fee_recipient:first,reserved_fee_recipients:rest};emit!(event.clone());emit_cpi!(event);Ok(())
    }

pub fn update_buyback_config(ctx:Context<AdminGlobal>,buyback_basis_points:Option<u64>)->Result<()>{
     let global=&mut ctx.accounts.global;
     if let Some(value)=buyback_basis_points{global.set_buyback_basis_points(value)?;}
     if ctx.remaining_accounts.is_empty(){return Ok(());}
     require!(ctx.remaining_accounts.len()==8,PumpError::WrongBuybackFeeRecipientsCount);
     let recipients=core::array::from_fn(|index|ctx.remaining_accounts[index].key());
     global.set_buyback_fee_recipients(recipients)
    }
