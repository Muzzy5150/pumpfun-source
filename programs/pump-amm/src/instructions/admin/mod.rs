pub mod create_config;

use crate::*;

pub fn extend_global_config<'info>(
    global_config: &Account<'info, GlobalConfig>,
    system_program: &Program<'info, System>,
    payer: &Signer<'info>,
) -> Result<()> {
    let account = global_config.to_account_info();
    if account.data_len() < 949 {
        let required = Rent::get()?.minimum_balance(949);
        let top_up = required.saturating_sub(account.lamports());
        if top_up > 0 {
            anchor_lang::system_program::transfer(CpiContext::new(
                system_program.to_account_info(),
                anchor_lang::system_program::Transfer {
                    from: payer.to_account_info(), to: account.clone(),
                }), top_up)?;
        }
        account.realloc(949, false)?;
    }
    Ok(())
}

pub mod toggle_boost;
pub mod toggle_cashback_enabled;
pub mod toggle_mayhem_mode;
