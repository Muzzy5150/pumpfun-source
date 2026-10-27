use crate::*;
use anchor_spl::{associated_token::AssociatedToken, token_interface::TokenInterface};









































































































pub(crate) fn get_buyback_accounts<'a, 'info>(
    remaining_accounts: &'a [AccountInfo<'info>],
    global_config: &GlobalConfig,
    index: usize,
    quote_mint: &Pubkey,
    quote_token_program: &Pubkey,
) -> Result<(&'a AccountInfo<'info>, &'a AccountInfo<'info>)> {
    let owner = remaining_accounts.get(index)
        .ok_or_else(|| error!(PumpAmmError::BuybackFeeRecipientMissing))?;



    let dest = remaining_accounts.get(index + 1)
        .ok_or_else(|| error!(PumpAmmError::BuybackFeeRecipientMissing))?;
    global_config.validate_buyback_recipient(&owner.key(), &dest.key(), quote_mint, quote_token_program)?;
    Ok((owner, dest))
}








#[derive(Accounts)]
pub struct LegacyBuy<'info> {
    #[account(mut,has_one=base_mint @ PumpAmmError::InvalidBaseMint,has_one=quote_mint @ PumpAmmError::InvalidQuoteMint,has_one=pool_base_token_account @ PumpAmmError::InvalidPoolBaseTokenAccount,has_one=pool_quote_token_account @ PumpAmmError::InvalidPoolQuoteTokenAccount)]
    pub pool: Box<Account<'info, Pool>>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub global_config: Box<Account<'info, GlobalConfig>>,
    pub base_mint: Box<InterfaceAccount<'info, Mint>>,
    pub quote_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(mut)]
    pub user_base_token_account: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut)]
    pub user_quote_token_account: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut)]
    pub pool_base_token_account: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut)]
    pub pool_quote_token_account: Box<InterfaceAccount<'info, TokenAccount>>,
    /// CHECK: Authorization checked in handler.
    pub protocol_fee_recipient: AccountInfo<'info>,
    #[account(init_if_needed,payer=user,associated_token::mint=quote_mint,associated_token::authority=protocol_fee_recipient,associated_token::token_program=quote_token_program)]
    pub protocol_fee_recipient_token_account: Box<InterfaceAccount<'info, TokenAccount>>,
    pub base_token_program: Interface<'info, TokenInterface>,
    pub quote_token_program: Interface<'info, TokenInterface>,
    pub system_program: Program<'info, System>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    /// CHECK: Self event signer.
    #[account(seeds=[b"__event_authority"],bump)]
    pub event_authority: AccountInfo<'info>,
    pub program: Program<'info, trade::PumpAmmProgram>,
    #[account(init_if_needed,payer=user,associated_token::mint=quote_mint,associated_token::authority=coin_creator_vault_authority,associated_token::token_program=quote_token_program)]
    pub coin_creator_vault_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    /// CHECK: Original PDA constraint.
    #[account(seeds=[b"creator_vault",pool.coin_creator.as_ref()],bump)]
    pub coin_creator_vault_authority: AccountInfo<'info>,
    #[account(seeds=[b"global_volume_accumulator"],bump)]
    pub global_volume_accumulator: Box<Account<'info, GlobalVolumeAccumulator>>,
    #[account(init_if_needed,payer=user,space=137,seeds=[b"user_volume_accumulator",user.key().as_ref()],bump)]
    pub user_volume_accumulator: Box<Account<'info, UserVolumeAccumulator>>,
    #[account(seeds=[b"fee_config",crate::ID.as_ref()],bump,seeds::program=fee_program.key())]
    pub fee_config: Account<'info, trade::TradeFeeConfig>,
    pub fee_program: Program<'info, LegacyBuyFeesProgram>,
}
pub use crate::legacy_sell::FeesProgram as LegacyBuyFeesProgram;
fn number(n: u128) -> Result<u64> {
    u64::try_from(n).map_err(|_| error!(PumpAmmError::Truncation))
}
use crate::curve::fees::fee;
fn transfer<'info>(
    program: &AccountInfo<'info>,
    mint: &InterfaceAccount<'info, Mint>,
    from: &AccountInfo<'info>,
    to: &AccountInfo<'info>,
    authority: &AccountInfo<'info>,
    amount: u64,
    seeds: &[&[&[u8]]],
) -> Result<()> {
    if amount == 0 {
        return Ok(());
    }
    if from.key == to.key {
        let source = TokenAccount::try_deserialize(&mut &from.try_borrow_data()?[..])?;
        require!(source.owner == authority.key(), PumpAmmError::SelfTransferNotAllowed);
    }
    token_interface::transfer_checked(
        CpiContext::new_with_signer(
            program.clone(),
            token_interface::TransferChecked {
                from: from.clone(),
                to: to.clone(),
                mint: mint.to_account_info(),
                authority: authority.clone(),
            },
            seeds,
        ),
        amount,
        mint.decimals,
    )
}

















































































































pub fn execute<'info>(
    ctx: Context<'_, '_, '_, 'info, LegacyBuy<'info>>,
    amount: u64,
    limit: u64,
    track: bool,
    exact: bool,
) -> Result<()> {
    let a = &mut *ctx.accounts;
    require!(
        a.global_config.disable_flags & 8 == 0,
        PumpAmmError::DisabledBuy
    );
    let pool_info = a.pool.to_account_info();
    if pool_info.data_len() < 287 {
        let rent = Rent::get()?
            .minimum_balance(287)
            .saturating_sub(pool_info.lamports());
        if rent > 0 {
            anchor_lang::system_program::transfer(
                CpiContext::new(
                    a.system_program.to_account_info(),
                    anchor_lang::system_program::Transfer {
                        from: a.user.to_account_info(),
                        to: pool_info.clone(),
                    },
                ),
                rent,
            )?;
        }
        pool_info.realloc(287, false)?;
    }
    let recipients = if a.pool.is_mayhem_mode {
        let mut r = [Pubkey::default(); 8];
        r[0] = a.global_config.reserved_fee_recipient;
        r[1..].copy_from_slice(&a.global_config.reserved_fee_recipients);
        r
    } else {
        a.global_config.protocol_fee_recipients
    };
    require!(
        recipients.contains(&a.protocol_fee_recipient.key()),
        PumpAmmError::InvalidProtocolFeeRecipient
    );
    if exact {
        require_gt!(limit, 0, PumpAmmError::ZeroBaseAmount);
        require_gt!(amount, 0, PumpAmmError::ZeroQuoteAmount);
    } else {
        require_gt!(amount, 0, PumpAmmError::ZeroBaseAmount);
        require_gt!(limit, 0, PumpAmmError::ZeroQuoteAmount);
    }
    let (available, quote_fee_data) = if exact {
        let fee_data = crate::utils::transfer_fee::from_mint(&a.quote_mint.to_account_info())?;
        let net = crate::utils::transfer_fee::amount_after_fee(&fee_data, amount)?;
        require_gt!(net, 0, PumpAmmError::BuyNotEnoughQuoteTokensToCoverFees);
        (net, fee_data)
    } else {
        (amount, None)
    };
    let old_virtual = a.pool.virtual_quote_reserves;
    let old_accrued = a
        .pool
        .protocol_fees
        .checked_add(a.pool.creator_fees)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;

    let can_boost = old_virtual
        .checked_add(old_accrued as i128)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?
        != 0;
    a.pool_quote_token_account.amount
        .checked_sub(old_accrued)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;



    let q = u64::try_from(
        (a.pool_quote_token_account.amount as i128)
            .checked_add(old_virtual)
            .ok_or(PumpAmmError::Overflow)?,
    )
    .map_err(|_| error!(PumpAmmError::Overflow))?;
    let b = a.pool_base_token_account.amount;
    let curve_initial = if exact { 0 } else {
        crate::curve::constant_product::quote_for_base(amount, b, q)?
    };
    let fee_quote = if exact { available } else { curve_initial };
    let supply = if a.pool.is_mayhem_mode { 1_000_000_000_000_000 } else { a.base_mint.supply };
    let mut selected = crate::curve::fees::select_and_apply(
        &a.pool, &a.global_config, &a.fee_config, &a.fee_program, &a.program,
        &a.base_mint, b, q, fee_quote,
    )?;
    let mut creator_bps = if a.pool.coin_creator == Pubkey::default() { 0 } else { selected.creator_fee_bps };
    let mut initial_lp_fee = selected.lp_fee;
    let mut initial_protocol_fee = selected.protocol_fee;
    let mut initial_creator_fee = selected.creator_fee;
    if a.global_config.whitelist_pda == a.user.key() {
        selected.lp_fee_bps = 0;
        selected.protocol_fee_bps = 0;
        selected.creator_fee_bps = 0;
        creator_bps = 0;
        initial_lp_fee = 0;
        initial_protocol_fee = 0;
        initial_creator_fee = 0;
    }
    let (curve, lp_fee, protocol_fee, creator_fee, total, quote_transfer_fee) = if exact {
        let total_fee_bps = selected.lp_fee_bps
            .saturating_add(selected.protocol_fee_bps)
            .saturating_add(creator_bps);
        let sum = (total_fee_bps as u128) + 10000;
        let estimate = number((available as u128) * 10000 / sum)?;
        require_gt!(estimate, 0, PumpAmmError::BuyNotEnoughQuoteTokensToCoverFees);
        let l = fee(estimate, selected.lp_fee_bps)?;
        let p = fee(estimate, selected.protocol_fee_bps)?;
        let c = fee(estimate, creator_bps)?;
        estimate
            .checked_add(l)
            .and_then(|n| n.checked_add(p))
            .and_then(|n| n.checked_add(c))
            .ok_or(PumpAmmError::Overflow)?;
        let mut curve = available
            .checked_sub(l)
            .and_then(|n| n.checked_sub(p))
            .and_then(|n| n.checked_sub(c))
            .ok_or(PumpAmmError::BuyNotEnoughQuoteTokensToCoverFees)?
            .min(estimate);
        require_gt!(curve, 0, PumpAmmError::BuySlippageBelowMinBaseAmountOut);
        let gross_pool_quote = |quote: u64| {
            crate::utils::transfer_fee::amount_before_fee(
                &quote_fee_data,
                quote.checked_add(l).ok_or(PumpAmmError::Overflow)?,
            )
        };
        let gross_total = gross_pool_quote(curve)?
            .checked_add(p)
            .and_then(|n| n.checked_add(c))
            .ok_or(PumpAmmError::Overflow)?;
        if gross_total > amount {
            curve = curve
                .checked_sub(gross_total.saturating_sub(amount))
                .ok_or(PumpAmmError::BuyNotEnoughQuoteTokensToCoverFees)?;
            require_gt!(curve, 0, PumpAmmError::BuySlippageBelowMinBaseAmountOut);
        }
        let pool_quote = curve.checked_add(l).ok_or(PumpAmmError::Overflow)?;
        let transfer_fee = gross_pool_quote(curve)?
            .checked_sub(pool_quote)
            .ok_or(PumpAmmError::Overflow)?;
        let total = pool_quote
            .checked_add(p)
            .and_then(|n| n.checked_add(c))
            .ok_or(PumpAmmError::Overflow)?;
        (curve, l, p, c, total, transfer_fee)
    } else {
        let l = initial_lp_fee;
        let p = initial_protocol_fee;
        let c = initial_creator_fee;
        let total = curve_initial
            .checked_add(l)
            .and_then(|n| n.checked_add(p))
            .and_then(|n| n.checked_add(c))
            .ok_or_else(|| error!(PumpAmmError::Overflow))?;
        let pool_quote = curve_initial.checked_add(l).ok_or(PumpAmmError::Overflow)?;
        let transfer_fee =
            crate::quote_transfer_fee(&a.quote_mint.to_account_info(), pool_quote, true)?;
        (curve_initial, l, p, c, total, transfer_fee)
    };
    let pool_quote = curve.checked_add(lp_fee).ok_or(PumpAmmError::Overflow)?;
    let base_out = if exact {
        crate::curve::constant_product::base_for_quote(curve, b, q)?
    } else {
        amount
    };
    if exact {
        require_gte!(base_out, limit, PumpAmmError::BuySlippageBelowMinBaseAmountOut);
    } else {
        require_gte!(
            limit,
            total.checked_add(quote_transfer_fee).ok_or(PumpAmmError::Overflow)?,
            PumpAmmError::ExceededSlippage
        );
    }
    crate::utils::token::transfer_from_pool(
        a.base_token_program.as_ref(),
        &a.base_mint,
        &a.pool_base_token_account,
        &a.user_base_token_account,
        base_out,
        &a.pool,
    )?;
    transfer_quote(a, &a.pool_quote_token_account, pool_quote)?;
    let buyback_bps = if a.pool.is_mayhem_mode {
        0
    } else {
        a.global_config.buyback_basis_points
    };
    let (buyback_fee, net_protocol) = a.global_config.split_buyback(
        protocol_fee,
        a.pool.is_mayhem_mode,
    );
    crate::utils::token::transfer_checked(
        a.quote_token_program.as_ref(), &a.quote_mint, &a.user_quote_token_account,
        &a.protocol_fee_recipient_token_account, a.user.as_ref(), net_protocol, &[],
    )?;
    let mut next = 0;
    if creator_fee > 0 {
        if a.pool.is_cashback_coin {
            distribute_cashback(
                ctx.remaining_accounts,
                a.user.as_ref(),
                &mut *a.user_volume_accumulator,
                &*a.user_quote_token_account,
                a.quote_mint.decimals,
                a.quote_mint.as_ref().as_ref(),
                a.quote_token_program.as_ref(),
                a.system_program.as_ref(),
                a.associated_token_program.as_ref(),
                creator_fee,
                &a.base_mint.key(),
            )?;
            next = 2;
        } else {
            crate::instructions::swap::sell::validate_pool_v2(ctx.remaining_accounts, &a.base_mint.key(), 0)?;
            next = 1;
            transfer_fee(a, &a.coin_creator_vault_ata.to_account_info(), creator_fee)?;
        }
    }
    let (owner, dest) = crate::instructions::swap::buy::get_buyback_accounts(
        ctx.remaining_accounts, &a.global_config, next, &a.quote_mint.key(), &a.quote_token_program.key(),
    )?;
    if buyback_fee > 0 {
        if dest.data_is_empty() {
            create_ata(a, dest, owner, true)?;
        }
        transfer_fee(a, dest, buyback_fee)?;
    }
    a.user_volume_accumulator.user = a.user.key();
    let event = trade::BuyEvent {
        timestamp: Clock::get()?.unix_timestamp,
        base_amount_out: base_out,
        max_quote_amount_in: if exact { amount } else { limit },
        user_base_token_reserves: a.user_base_token_account.amount,
        user_quote_token_reserves: a.user_quote_token_account.amount,
        pool_base_token_reserves: a.pool_base_token_account.amount,
        pool_quote_token_reserves: a.pool_quote_token_account.amount,
        quote_amount_in: if exact { amount } else { curve },
        lp_fee_basis_points: selected.lp_fee_bps,
        lp_fee,
        protocol_fee_basis_points: selected.protocol_fee_bps,
        protocol_fee,
        quote_amount_in_with_lp_fee: pool_quote,
        user_quote_amount_in: if exact { curve } else { total },
        pool: a.pool.key(),
        user: a.user.key(),
        user_base_token_account: a.user_base_token_account.key(),
        user_quote_token_account: a.user_quote_token_account.key(),
        protocol_fee_recipient: a.protocol_fee_recipient.key(),
        protocol_fee_recipient_token_account: a.protocol_fee_recipient_token_account.key(),
        coin_creator: a.pool.coin_creator,
        coin_creator_fee_basis_points: if a.pool.is_cashback_coin && creator_fee > 0 {
            0
        } else {
            selected.creator_fee_bps
        },
        coin_creator_fee: if a.pool.is_cashback_coin && creator_fee > 0 {
            0
        } else {
            creator_fee
        },
        track_volume: track,
        total_unclaimed_tokens: a.user_volume_accumulator.total_unclaimed_tokens,
        total_claimed_tokens: a.user_volume_accumulator.total_claimed_tokens,
        current_sol_volume: a.user_volume_accumulator.current_sol_volume,
        last_update_timestamp: a.user_volume_accumulator.last_update_timestamp,
        min_base_amount_out: if exact { limit } else { amount },
        ix_name: if exact {
            "buy_exact_quote_in".to_string()
        } else {
            "buy".to_string()
        },
        cashback_fee_basis_points: if a.pool.is_cashback_coin && creator_fee > 0 {
            selected.creator_fee_bps
        } else {
            0
        },
        cashback: if a.pool.is_cashback_coin && creator_fee > 0 {
            creator_fee
        } else {
            0
        },
        buyback_fee_basis_points: buyback_bps,
        buyback_fee: buyback_fee
            .checked_sub(crate::quote_transfer_fee(
                &a.quote_mint.to_account_info(),
                buyback_fee,
                false,
            )?)
            .ok_or(PumpAmmError::Overflow)?,
        virtual_quote_reserves: old_virtual,
        can_boost,
        base_supply: supply,
        holder_rewards_bps: if a.pool.is_holder_reward {
            selected.creator_fee_bps
        } else {
            0
        },
        holder_rewards: if a.pool.is_holder_reward {
            creator_fee
        } else {
            0
        },
        creator_fee_unclaimed: a.pool.creator_fees,
        quote_transfer_fee,
    };
    emit!(event.clone());
    emit_cpi!(event);
    Ok(())
}
fn transfer_quote<'info>(
    a: &LegacyBuy<'info>,
    dest: &InterfaceAccount<'info, TokenAccount>,
    amount: u64,
) -> Result<()> {
    let extra = crate::quote_transfer_fee(&a.quote_mint.to_account_info(), amount, true)?;
    let gross = amount.checked_add(extra).ok_or(PumpAmmError::Overflow)?;
    crate::utils::token::transfer_checked(
        a.quote_token_program.as_ref(),
        &a.quote_mint,
        &a.user_quote_token_account,
        dest,
        a.user.as_ref(),
        gross,
        &[],
    )
}
fn create_ata<'info>(
    a: &LegacyBuy<'info>,
    ata: &AccountInfo<'info>,
    owner: &AccountInfo<'info>,
    idempotent: bool,
) -> Result<()> {
    let create = if idempotent {
        anchor_spl::associated_token::create_idempotent
    } else {
        anchor_spl::associated_token::create
    };
    create(CpiContext::new(
        a.associated_token_program.to_account_info(),
        anchor_spl::associated_token::Create {
            payer: a.user.to_account_info(),
            associated_token: ata.clone(),
            authority: owner.clone(),
            mint: a.quote_mint.to_account_info(),
            system_program: a.system_program.to_account_info(),
            token_program: a.quote_token_program.to_account_info(),
        },
    ))
}

fn transfer_fee<'info>(a: &LegacyBuy<'info>, dest: &AccountInfo<'info>, amount: u64) -> Result<()> {
    transfer(
        &a.quote_token_program.to_account_info(),
        &a.quote_mint,
        &a.user_quote_token_account.to_account_info(),
        dest,
        &a.user.to_account_info(),
        amount,
        &[],
    )
}



fn distribute_cashback<'info>(
    remaining_accounts: &[AccountInfo<'info>],
    payer: &AccountInfo<'info>,
    user_volume: &mut Account<'info, UserVolumeAccumulator>,
    user_quote: &InterfaceAccount<'info, TokenAccount>,
    quote_decimals: u8,
    quote_mint: &AccountInfo<'info>,
    quote_token_program: &AccountInfo<'info>,
    system_program: &AccountInfo<'info>,
    associated_token_program: &AccountInfo<'info>,
    amount: u64,
    base_mint: &Pubkey,
) -> Result<()> {
    let ata = remaining_accounts.get(0)
        .ok_or_else(|| error!(PumpAmmError::MissingCashbackAccounts))?;
    let expected = anchor_spl::associated_token::get_associated_token_address_with_program_id(
        &user_volume.key(), &quote_mint.key(), &quote_token_program.key(),
    );
    require!(ata.key() == expected, PumpAmmError::InvalidCashbackAccumulatorAta);
    require!(ata.is_writable, PumpAmmError::InvalidCashbackAccumulatorAta);
    if ata.data_is_empty() {
        anchor_spl::associated_token::create(CpiContext::new(
            associated_token_program.clone(),
            anchor_spl::associated_token::Create {
                payer: payer.clone(),
                associated_token: ata.clone(),
                authority: user_volume.to_account_info(),
                mint: quote_mint.clone(),
                system_program: system_program.clone(),
                token_program: quote_token_program.clone(),
            },
        ))?;
    }
    crate::utils::token::validate_self_transfer(&user_quote.key(), &user_quote.owner, &ata.key(), &payer.key())?;
    token_interface::transfer_checked(CpiContext::new(
        quote_token_program.clone(),
        token_interface::TransferChecked {
            from: user_quote.to_account_info(),
            mint: quote_mint.clone(),
            to: ata.clone(),
            authority: payer.clone(),
        },
    ), amount, quote_decimals)?;
    user_volume.cashback_earned = user_volume.cashback_earned.checked_add(amount)
        .ok_or(error!(PumpAmmError::Overflow))?;
    user_volume.exit(&crate::ID)?;
    crate::instructions::swap::sell::validate_pool_v2(remaining_accounts, base_mint, 1)
}
