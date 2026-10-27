use crate::*;




















































pub fn deposit(ctx: Context<Liquidity>, amount: u64, base_limit: u64, quote_limit: u64) -> Result<()> {
    let a = &mut *ctx.accounts;
    require!(a.global_config.disable_flags & 2 == 0, PumpAmmError::DisabledDeposit);
    let base_reserve = a.pool_base_token_account.amount;
    let user_quote_token_reserves = a.user_quote_token_account.amount;
    let user_base_token_reserves = a.user_base_token_account.amount;
    let pool_quote_token_reserves = a.pool_quote_token_account.amount;
    let quote_reserve = liquidity_quote_reserves(&a.pool, pool_quote_token_reserves)?;
    let old_supply = a.pool.lp_supply;












    let base_amount = u64::try_from(crate::curve::fees::ceil_div(
        (base_reserve as u128) * (amount as u128), old_supply as u128,
    )?).map_err(|_| error!(PumpAmmError::Truncation))?;

    require_gte!(base_limit, base_amount, PumpAmmError::ExceededSlippage);









    let quote_amount = u64::try_from(crate::curve::fees::ceil_div(
        (quote_reserve as u128) * (amount as u128), old_supply as u128,
    )?).map_err(|_| error!(PumpAmmError::Truncation))?;




    let fee_data = crate::utils::transfer_fee::from_mint(&a.quote_mint.to_account_info())?;
    let quote_transfer_amount = crate::utils::transfer_fee::amount_before_fee(&fee_data, quote_amount)?;
    let quote_transfer_fee = quote_transfer_amount.checked_sub(quote_amount)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    require_gte!(quote_limit, quote_transfer_amount, PumpAmmError::ExceededSlippage);
    let base_program = if *a.base_mint.to_account_info().owner == anchor_spl::token::ID {
        a.token_program.as_ref()
    } else {
        a.token_2022_program.as_ref()
    };
    crate::utils::token::transfer_checked(base_program, &a.base_mint,
        &a.user_base_token_account, &a.pool_base_token_account,
        a.user.as_ref(), base_amount, &[])?;
    let quote_program = if *a.quote_mint.to_account_info().owner == anchor_spl::token::ID {
        a.token_program.as_ref()
    } else {
        a.token_2022_program.as_ref()
    };
    crate::utils::token::transfer_checked(quote_program, &a.quote_mint,
        &a.user_quote_token_account, &a.pool_quote_token_account,
        a.user.as_ref(), quote_transfer_amount, &[])?;
    crate::utils::token::mint_to_pool(&a.token_2022_program, &a.lp_mint,
        &a.user_pool_token_account, amount, &a.pool)?;























    a.pool.lp_supply = a.pool.lp_supply.checked_add(amount)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    if a.pool.can_boost() {
        let effective_virtual = liquidity_effective_virtual(&a.pool)?;





        let virtual_reserve = u128::try_from(effective_virtual)
            .map_err(|_| error!(PumpAmmError::Overflow))?;
        let change = virtual_reserve.checked_mul(amount as u128)
            .ok_or_else(|| error!(PumpAmmError::Overflow))?
            .checked_div(old_supply as u128)
                .ok_or_else(|| error!(PumpAmmError::DivisionByZero))?;



        let change = i128::try_from(change).map_err(|_| error!(PumpAmmError::Overflow))?;
        a.pool.virtual_quote_reserves = a.pool.virtual_quote_reserves.checked_add(change)
            .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    }
    let event = DepositEvent {
        timestamp: Clock::get()?.unix_timestamp,
        lp_token_amount_out: amount,
        max_base_amount_in: base_limit,
        max_quote_amount_in: quote_limit,
        user_base_token_reserves,
        user_quote_token_reserves,
        pool_base_token_reserves: base_reserve,
        pool_quote_token_reserves,
        base_amount_in: base_amount,
        quote_amount_in: quote_amount,
        lp_mint_supply: old_supply,
        pool: a.pool.key(),
        user: a.user.key(),
        user_base_token_account: a.user_base_token_account.key(),
        user_quote_token_account: a.user_quote_token_account.key(),
        user_pool_token_account: a.user_pool_token_account.key(),
        quote_transfer_fee,
    };
    emit!(event);
    emit_cpi!(event);
    Ok(())
}
