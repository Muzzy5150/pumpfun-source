use crate::*;
use anchor_spl::{associated_token::AssociatedToken, token_interface::TokenInterface};
#[derive(Accounts)]
pub struct LegacySell<'info> {
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
    #[account(seeds=[b"fee_config",crate::ID.as_ref()],bump,seeds::program=fee_program.key())]
    pub fee_config: Account<'info, trade::TradeFeeConfig>,
    pub fee_program: Program<'info, FeesProgram>,
}
pub struct FeesProgram;
impl Id for FeesProgram {
    fn id() -> Pubkey {
        trade::FEE_OWNER
    }
}
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
    ctx: Context<'_, '_, '_, 'info, LegacySell<'info>>,
    amount: u64,
    limit: u64,
) -> Result<()> {
    let a = &mut *ctx.accounts;
    require!(
        a.global_config.disable_flags & 16 == 0,
        PumpAmmError::DisabledSell
    );
    let pool_info = a.pool.to_account_info();
    if pool_info.data_len() < 287 {
        let need = Rent::get()?
            .minimum_balance(287)
            .saturating_sub(pool_info.lamports());
        if need > 0 {
            anchor_lang::system_program::transfer(
                CpiContext::new(
                    a.system_program.to_account_info(),
                    anchor_lang::system_program::Transfer {
                        from: a.user.to_account_info(),
                        to: pool_info.clone(),
                    },
                ),
                need,
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
    require_gt!(amount, 0, PumpAmmError::ZeroBaseAmount);
    let old_virtual = a.pool.virtual_quote_reserves;
    let q = u64::try_from(
        (a.pool_quote_token_account.amount as i128)
            .checked_add(old_virtual)
            .ok_or_else(|| error!(PumpAmmError::Overflow))?,
    )
    .map_err(|_| error!(PumpAmmError::Overflow))?;
    // Legacy pricing uses the requested gross base input, including for Token-2022.
    let base_amount = amount;
    let quote = crate::curve::constant_product::quote_for_sell(
        base_amount, a.pool_base_token_account.amount, q,
    )?;
    let supply = if a.pool.is_mayhem_mode { 1_000_000_000_000_000 } else { a.base_mint.supply };
    let mut selected = crate::curve::fees::select_and_apply(
        &a.pool, &a.global_config, &a.fee_config, &a.fee_program, &a.program,
        &a.base_mint, a.pool_base_token_account.amount, q, quote,
    )?;
    let mut lp_fee = selected.lp_fee;
    let mut protocol_fee = selected.protocol_fee;
    let mut creator_fee = selected.creator_fee;
    if a.global_config.whitelist_pda == a.user.key() {
        selected.lp_fee_bps = 0;
        selected.protocol_fee_bps = 0;
        selected.creator_fee_bps = 0;
        lp_fee = 0;
        protocol_fee = 0;
        creator_fee = 0;
    }
    let quote_less_lp = quote
        .checked_sub(lp_fee)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    let old_accrued = a
        .pool
        .protocol_fees
        .checked_add(a.pool.creator_fees)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    let real_quote = a
        .pool_quote_token_account
        .amount
        .checked_sub(old_accrued)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    require_gte!(
        real_quote,
        quote_less_lp,
        PumpAmmError::InsufficientRealQuoteReserves
    );
    let total = quote_less_lp
        .checked_sub(creator_fee)
        .and_then(|n| n.checked_sub(protocol_fee))
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    let quote_transfer_fee = quote_transfer_fee(&a.quote_mint.to_account_info(), total, false)?;
    require_gte!(
        total.checked_sub(quote_transfer_fee).ok_or(PumpAmmError::Overflow)?,
        limit,
        PumpAmmError::ExceededSlippage
    );
    let index = a.pool.index.to_le_bytes();
    let bump = [a.pool.pool_bump];
    let creator = a.pool.creator;
    let base = a.pool.base_mint;
    let quote_mint = a.pool.quote_mint;
    let seeds: &[&[u8]] = &[
        b"pool",
        &index,
        creator.as_ref(),
        base.as_ref(),
        quote_mint.as_ref(),
        &bump,
    ];
    let signer = &[seeds];
    crate::utils::token::transfer_checked(
        a.base_token_program.as_ref(),
        &a.base_mint,
        &a.user_base_token_account,
        &a.pool_base_token_account,
        &a.user.to_account_info(),
        amount,
        &[],
    )?;
    crate::utils::token::transfer_from_pool(
        a.quote_token_program.as_ref(),
        &a.quote_mint,
        &a.pool_quote_token_account,
        &a.user_quote_token_account,
        total,
        &a.pool,
    )?;
    let buyback_bps = if a.pool.is_mayhem_mode {
        0
    } else {
        a.global_config.buyback_basis_points
    };
    let (buyback_fee, net_protocol) = a.global_config.split_buyback(
        protocol_fee,
        a.pool.is_mayhem_mode,
    );
    crate::utils::token::transfer_from_pool(
        a.quote_token_program.as_ref(),
        &a.quote_mint,
        &a.pool_quote_token_account,
        &a.protocol_fee_recipient_token_account,
        net_protocol,
        &a.pool,
    )?;
    // Payouts consume remaining accounts only when a creator/cashback fee is nonzero.
    let mut next = 0;
    if creator_fee > 0 {
        if a.pool.is_cashback_coin && creator_fee > 0 {
            cashback(a, ctx.remaining_accounts, creator_fee, signer)?;
            next = 2;
        }
        crate::instructions::swap::sell::validate_pool_v2(ctx.remaining_accounts, &a.base_mint.key(), next)?;
        next += 1;
        if !a.pool.is_cashback_coin {
            crate::utils::token::transfer_from_pool(
        a.quote_token_program.as_ref(),
        &a.quote_mint,
        &a.pool_quote_token_account,
        &a.coin_creator_vault_ata,
        creator_fee,
        &a.pool,
    )?;
        }
    }
    {
    let (owner, dest) = crate::instructions::swap::buy::get_buyback_accounts(
        ctx.remaining_accounts, &a.global_config, next, &a.quote_mint.key(), &a.quote_token_program.key(),
    )?;
        if buyback_fee > 0 && dest.data_is_empty() {
            create_ata(a, dest, owner, true)?;
        }
        crate::utils::token::transfer_from_pool_to_raw(
            a.quote_token_program.as_ref(),
            &a.quote_mint,
            &a.pool_quote_token_account,
            &a.pool,
            dest,
            buyback_fee,
        )?;
    }
    let event = trade::SellEvent {
        timestamp: Clock::get()?.unix_timestamp,
        base_amount_in: amount,
        min_quote_amount_out: limit,
        user_base_token_reserves: a.user_base_token_account.amount,
        user_quote_token_reserves: a.user_quote_token_account.amount,
        pool_base_token_reserves: a.pool_base_token_account.amount,
        pool_quote_token_reserves: a.pool_quote_token_account.amount,
        quote_amount_out: quote,
        lp_fee_basis_points: selected.lp_fee_bps,
        lp_fee,
        protocol_fee_basis_points: selected.protocol_fee_bps,
        protocol_fee,
        quote_amount_out_without_lp_fee: quote - lp_fee,
        user_quote_amount_out: total,
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
        can_boost: old_virtual
            .checked_add(old_accrued as i128)
            .ok_or(PumpAmmError::Overflow)?
            != 0,
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

fn create_ata<'info>(
    a: &LegacySell<'info>,
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
fn cashback<'info>(
    a: &LegacySell<'info>,
    remaining: &[AccountInfo<'info>],
    amount: u64,
    seeds: &[&[&[u8]]],
) -> Result<()> {
    let ata = remaining
        .get(0)
        .ok_or_else(|| error!(PumpAmmError::MissingCashbackAccounts))?;
    let info = remaining
        .get(1)
        .ok_or_else(|| error!(PumpAmmError::MissingCashbackAccounts))?;
    let user = a.user.key();
    let (key, bump) =
        Pubkey::find_program_address(&[b"user_volume_accumulator", user.as_ref()], &crate::ID);
    require!(info.key() == key, PumpAmmError::InvalidCashbackAccumulator);
    require!(info.is_writable, PumpAmmError::InvalidCashbackAccumulator);
    if info.data_is_empty() {
        let rent = Rent::get()?.minimum_balance(137);
        if rent > info.lamports() {
            anchor_lang::system_program::transfer(
                CpiContext::new(
                    a.system_program.to_account_info(),
                    anchor_lang::system_program::Transfer {
                        from: a.user.to_account_info(),
                        to: info.clone(),
                    },
                ),
                rent - info.lamports(),
            )?;
        }
        let bump = [bump];
        let init_seeds: &[&[u8]] = &[b"user_volume_accumulator", user.as_ref(), &bump];
        anchor_lang::system_program::allocate(
            CpiContext::new_with_signer(
                a.system_program.to_account_info(),
                anchor_lang::system_program::Allocate {
                    account_to_allocate: info.clone(),
                },
                &[init_seeds],
            ),
            137,
        )?;
        anchor_lang::system_program::assign(
            CpiContext::new_with_signer(
                a.system_program.to_account_info(),
                anchor_lang::system_program::Assign {
                    account_to_assign: info.clone(),
                },
                &[init_seeds],
            ),
            &crate::ID,
        )?;
        info.try_borrow_mut_data()?[..8].copy_from_slice(UserVolumeAccumulator::DISCRIMINATOR);
    } else {
        require!(*info.owner == crate::ID, PumpAmmError::InvalidCashbackAccumulator);
        let data = info.try_borrow_data()?;
        require!(
            data.len() >= 8 && &data[..8] == UserVolumeAccumulator::DISCRIMINATOR,
            PumpAmmError::InvalidCashbackAccumulator
        );
    }
    let mut accumulator =
        UserVolumeAccumulator::try_deserialize(&mut &info.try_borrow_data()?[..])?;
    let expected = anchor_spl::associated_token::get_associated_token_address_with_program_id(
        info.key,
        &a.quote_mint.key(),
        &a.quote_token_program.key(),
    );
    require!(ata.key() == expected, PumpAmmError::InvalidCashbackAccumulatorAta);
    require!(ata.is_writable, PumpAmmError::InvalidCashbackAccumulatorAta);
    if ata.data_is_empty() {
        create_ata(a, ata, info, false)?;
    } else {
        <TokenAccount as anchor_lang::CheckOwner>::check_owner(ata.owner)?;
        TokenAccount::try_deserialize(&mut &ata.try_borrow_data()?[..])?;
    }
    transfer(
        &a.quote_token_program.to_account_info(),
        &a.quote_mint,
        &a.pool_quote_token_account.to_account_info(),
        ata,
        &a.pool.to_account_info(),
        amount,
        seeds,
    )?;
    accumulator.user = user;
    accumulator.cashback_earned = accumulator
        .cashback_earned
        .checked_add(amount)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    accumulator.try_serialize(&mut &mut info.try_borrow_mut_data()?[..])?;
    Ok(())
}
