use crate::*;





















































pub fn withdraw(ctx: Context<Liquidity>, amount: u64, base_limit: u64, quote_limit: u64) -> Result<()> {
    let a = &mut *ctx.accounts;
    require!(a.global_config.disable_flags & 4 == 0, PumpAmmError::DisabledWithdraw);




    require_gte!(a.pool.lp_supply, a.lp_mint.supply, PumpAmmError::SeedLockViolation);
    let base_reserve = a.pool_base_token_account.amount;
    let user_quote_token_reserves = a.user_quote_token_account.amount;
    let user_base_token_reserves = a.user_base_token_account.amount;
    let pool_quote_token_reserves = a.pool_quote_token_account.amount;
    let quote_reserve = liquidity_quote_reserves(&a.pool, pool_quote_token_reserves)?;
    let old_supply = a.pool.lp_supply;













    let base_amount = u64::try_from(crate::curve::constant_product::liquidity_floor_ratio(
        base_reserve, amount, old_supply,
    )?).map_err(|_| error!(PumpAmmError::Truncation))?;

    require_gte!(base_amount, base_limit, PumpAmmError::ExceededSlippage);









    let quote_amount = u64::try_from(crate::curve::constant_product::liquidity_floor_ratio(
        quote_reserve, amount, old_supply,
    )?).map_err(|_| error!(PumpAmmError::Truncation))?;




    let fee_data = crate::utils::transfer_fee::from_mint(&a.quote_mint.to_account_info())?;
    let quote_received = crate::utils::transfer_fee::amount_after_fee(&fee_data, quote_amount)?;
    let quote_transfer_fee = quote_amount.checked_sub(quote_received)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    require_gte!(quote_received, quote_limit, PumpAmmError::ExceededSlippage);
    let base_program = if *a.base_mint.to_account_info().owner == anchor_spl::token::ID {
        a.token_program.as_ref()
    } else {
        a.token_2022_program.as_ref()
    };
    crate::utils::token::transfer_from_pool(base_program, &a.base_mint,
        &a.pool_base_token_account, &a.user_base_token_account, base_amount, &a.pool)?;
    let quote_program = if *a.quote_mint.to_account_info().owner == anchor_spl::token::ID {
        a.token_program.as_ref()
    } else {
        a.token_2022_program.as_ref()
    };
    crate::utils::token::transfer_from_pool(quote_program, &a.quote_mint,
        &a.pool_quote_token_account, &a.user_quote_token_account, quote_amount, &a.pool)?;
    crate::utils::token::burn_from_user(&a.token_2022_program, &a.lp_mint,
        &a.user_pool_token_account, a.user.as_ref(), amount)?;

























    a.pool.lp_supply = a.pool.lp_supply.checked_sub(amount)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    if a.pool.can_boost() {
        let effective_virtual = liquidity_effective_virtual(&a.pool)?;






        let virtual_reserve = u128::try_from(effective_virtual)
            .map_err(|_| error!(PumpAmmError::Overflow))?;
        let change = crate::curve::fees::ceil_div(virtual_reserve.checked_mul(amount as u128)
                .ok_or_else(|| error!(PumpAmmError::Overflow))?,
            old_supply as u128,
        )?;

        let change = u64::try_from(change).map_err(|_| error!(PumpAmmError::Truncation))?;
        let change = i128::from(change);

        a.pool.virtual_quote_reserves = a.pool.virtual_quote_reserves.checked_sub(change)
            .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    }
    let event = WithdrawEvent {
        timestamp: Clock::get()?.unix_timestamp,
        lp_token_amount_in: amount,
        min_base_amount_out: base_limit,
        min_quote_amount_out: quote_limit,
        user_base_token_reserves,
        user_quote_token_reserves,
        pool_base_token_reserves: base_reserve,
        pool_quote_token_reserves,
        base_amount_out: base_amount,
        quote_amount_out: quote_amount,
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
