use anchor_lang::prelude::*;
use crate::{distribution::SharingConfig, PumpError};

pub(crate) fn execute_native_distribution<'info>(
    sharing_config: &Account<'info, SharingConfig>,
    creator_vault: &AccountInfo<'info>,
    system_program: &Program<'info, System>,
    remaining_accounts: &[AccountInfo<'info>],
    transfers: &[(u64, u64)],
    bump: u8,
) -> Result<u64> {
    let sharing_config_key = sharing_config.key();
    let creator_vault = creator_vault.to_account_info();
    let mut distributed = 0u64;
    for (index, _) in sharing_config.shareholders.iter().enumerate() {
        let recipient = remaining_accounts
            .get(index)
            .ok_or_else(|| error!(PumpError::NotEnoughRemainingAccounts))?;
        let amount = transfers[index].0;
        let bump = [bump];
        let seeds: &[&[u8]] = &[b"creator-vault", sharing_config_key.as_ref(), &bump];
        crate::collect_v2::transfer_native(
            system_program.as_ref(),
            &creator_vault,
            recipient,
            amount,
            &[seeds],
        )?;
        distributed = distributed
            .checked_add(amount)
            .ok_or_else(|| error!(PumpError::Overflow))?;
    }
    Ok(distributed)
}

use crate::trade_types::Shareholder;

#[event]
#[derive(Clone)]pub struct DistributeCreatorFeesEvent{pub timestamp:i64,pub mint:Pubkey,pub bonding_curve:Pubkey,pub sharing_config:Pubkey,pub admin:Pubkey,pub shareholders:Vec<Shareholder>,pub distributed:u64,pub quote_mint:Pubkey}
