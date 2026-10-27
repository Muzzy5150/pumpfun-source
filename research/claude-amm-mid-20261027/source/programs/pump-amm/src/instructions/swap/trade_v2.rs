use crate::*;
use crate::curve::fees::AppliedFees;
use crate::utils::transfer_fee::{self, TransferFeeData};

#[inline(never)]
pub fn validate_cashback_coin(is_cashback_coin: u8) -> Result<()> {
    require!(is_cashback_coin == 0, PumpAmmError::CashbackCoinNotSupported);
    Ok(())
}

#[inline(never)]
pub fn validate_buyback_token_account(
    global_config: &GlobalConfig,
    token_account: &AccountInfo,
    quote_mint: &Pubkey,
    token_program: &Pubkey,
) -> Result<()> {
    require_keys_eq!(*token_account.owner, *token_program, PumpAmmError::AccountTypeNotSupported);
    let owner = {
        let data = token_account.try_borrow_data()?;
        let mut data_slice = data.as_ref();
        let state = TokenAccount::try_deserialize(&mut data_slice)?;
        require_keys_eq!(state.mint, *quote_mint, PumpAmmError::InvalidQuoteMint);
        state.owner
    };
    global_config.validate_buyback_recipient(&owner, &token_account.key(), quote_mint, token_program)
}

#[inline(never)]
pub fn quote_reserves(pool: &Pool, raw_quote_reserves: u64) -> Result<(u64, u64)> {
    let available = pool.available_quote_reserves(raw_quote_reserves)?;
    let effective = pool.effective_quote_reserves(raw_quote_reserves)?;
    Ok((available, effective))
}

pub struct BuyResult {
    pub fees: AppliedFees,
    pub base_amount_out: u64,
    pub quote_amount_in: u64,
    pub user_quote_amount_in: u64,
    pub buyback_fee: u64,
    pub pool_quote_amount_in: u64,
    pub quote_transfer_fee: u64,
}

#[inline(never)]
fn total_quote(amounts: &[u64; 4]) -> Result<u64> {
    amounts.iter().try_fold(0u64, |total, amount| {
        total.checked_add(*amount).ok_or_else(|| error!(PumpAmmError::Overflow))
    })
}

#[inline(never)]
pub fn calculate_buy_result(
    buyback_basis_points: u64,
    is_mayhem_mode: u8,
    quote_transfer_fee: &TransferFeeData,
    base_amount_out: u64,
    quote_amount_in: u64,
    fees: &AppliedFees,
) -> Result<BuyResult> {
    let user_quote_amount_in = total_quote(&[
        quote_amount_in, fees.lp_fee, fees.protocol_fee, fees.creator_fee,
    ])?;
    let buyback_fee = if is_mayhem_mode == 0 {
        let buyback_fee = u64::try_from(
            (fees.protocol_fee as u128) * (buyback_basis_points as u128) / 10_000,
        ).expect("buyback fee is at most protocol_fee");
        fees.protocol_fee.checked_sub(buyback_fee)
            .expect("buyback_fee never exceeds protocol_fee");
        buyback_fee
    } else { 0 };
    let net_pool_quote = user_quote_amount_in.checked_sub(buyback_fee)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    let pool_quote_amount_in = transfer_fee::amount_before_fee(quote_transfer_fee, net_pool_quote)?;
    let quote_transfer_fee = pool_quote_amount_in.checked_sub(net_pool_quote)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    Ok(BuyResult {
        fees: fees.clone(),
        base_amount_out,
        quote_amount_in,
        user_quote_amount_in,
        buyback_fee,
        pool_quote_amount_in,
        quote_transfer_fee,
    })
}

impl BuyResult {
    pub fn total_user_quote(&self) -> Result<u64> {
        self.pool_quote_amount_in.checked_add(self.buyback_fee)
            .ok_or_else(|| error!(PumpAmmError::Overflow))
    }
}

pub struct BuyPreviewContext<'a, 'info> {
    pub pool: &'a Box<Account<'info, Pool>>,
    pub global_config: &'a Box<Account<'info, GlobalConfig>>,
    pub quote_transfer_fee: &'a TransferFeeData,
    pub fees: &'a AppliedFees,
}

#[inline(never)]
pub fn preview_total_quote(context: BuyPreviewContext, quote_amount_in: u64) -> Result<u64> {
    let global_config = context.global_config.as_ref();
    let pool = context.pool.as_ref();
    let quote_transfer_fee = context.quote_transfer_fee;
    let result = {
        let fees = context.fees.clone();
        calculate_buy_result(
            global_config.buyback_basis_points,
            pool.is_mayhem_mode as u8,
            quote_transfer_fee,
            0,
            quote_amount_in,
            &fees,
        )
    }?;
    result.total_user_quote()
}

/// Returns the quote after LP fees and the quote paid to the seller.
#[inline(never)]
pub fn calculate_sell_quote(
    quote_amount_out: u64,
    fees: &AppliedFees,
    real_quote_reserves: u64,
) -> Result<(u64, u64)> {
    let quote_amount_out_without_lp_fee = quote_amount_out.checked_sub(fees.lp_fee)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    require_gte!(real_quote_reserves, quote_amount_out_without_lp_fee,
        PumpAmmError::InsufficientRealQuoteReserves);
    let user_quote_amount_out = quote_amount_out_without_lp_fee.checked_sub(fees.creator_fee)
        .and_then(|amount| amount.checked_sub(fees.protocol_fee))
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    Ok((quote_amount_out_without_lp_fee, user_quote_amount_out))
}

pub struct TradeEventContext<'a, 'info> {
    pub pool: &'a Account<'info, Pool>,
    pub global_config: &'a GlobalConfig,
    pub user_volume_accumulator: &'a UserVolumeAccumulator,
    pub base_supply: u64,
    pub user: Pubkey,
    pub user_base_token_account: Pubkey,
    pub user_quote_token_account: Pubkey,
}

#[inline(never)]
pub fn create_sell_event(
    context: TradeEventContext,
    base_amount: u64,
    limit: u64,
    user_base_reserves: u64,
    user_quote_reserves: u64,
    b: u64,
    raw_quote_reserves: u64,
    curve_quote: u64,
    selected: &AppliedFees,
    quote_without_lp_fee: u64,
    total_quote: u64,
    old_virtual: i128,
    buyback_received: u64,
    quote_transfer_fee: u64,
) -> Result<crate::trade::SellEvent> {
    let pool = context.pool;
    let global_config = context.global_config;
    let base_supply = context.base_supply;
    let user = context.user;
    let user_base_token_account = context.user_base_token_account;
    let user_quote_token_account = context.user_quote_token_account;
    let timestamp = Clock::get()?.unix_timestamp;
        let event = crate::trade::SellEvent {
            timestamp,
            base_amount_in: base_amount,
            min_quote_amount_out: limit,
            user_base_token_reserves: user_base_reserves,
            user_quote_token_reserves: user_quote_reserves,
            pool_base_token_reserves: b,
            pool_quote_token_reserves: raw_quote_reserves,
            quote_amount_out: curve_quote,
            lp_fee_basis_points: selected.lp_fee_bps,
            lp_fee: selected.lp_fee,
            protocol_fee_basis_points: selected.protocol_fee_bps,
            protocol_fee: selected.protocol_fee,
            quote_amount_out_without_lp_fee: quote_without_lp_fee,
            user_quote_amount_out: total_quote,
            pool: pool.key(),
            protocol_fee_recipient: Pubkey::default(),
            protocol_fee_recipient_token_account: Pubkey::default(),
            coin_creator: pool.coin_creator,
            coin_creator_fee_basis_points: selected.creator_fee_bps,
            coin_creator_fee: selected.creator_fee,
            cashback_fee_basis_points: 0,
            cashback: 0,
            buyback_fee: buyback_received,
            virtual_quote_reserves: old_virtual,
            user,
            user_base_token_account,
            user_quote_token_account,
            holder_rewards_bps: if pool.is_holder_reward { selected.creator_fee_bps } else { 0 },
            holder_rewards: if pool.is_holder_reward { selected.creator_fee } else { 0 },
            buyback_fee_basis_points: if pool.is_mayhem_mode { 0 } else { global_config.buyback_basis_points },
            base_supply: if pool.is_mayhem_mode {1_000_000_000_000_000} else {base_supply},
            can_boost: pool.can_boost(),
            creator_fee_unclaimed: pool.creator_fees,
            quote_transfer_fee,
        };
    Ok(event)
}

#[inline(never)]
pub fn create_buy_event(
    context: TradeEventContext,
    result: &BuyResult,
    max_quote_amount_in: u64,
    min_base_amount_out: u64,
    quote_amount_in: u64,
    user_quote_amount_in: u64,
    user_base_reserves: u64,
    user_quote_reserves: u64,
    b: u64,
    raw_quote_reserves: u64,
    old_virtual: i128,
    buyback_received: u64,
    ix_name: &str,
) -> Result<crate::trade::BuyEvent> {
    let pool = context.pool;
    let global_config = context.global_config;
    let base_supply = context.base_supply;
    let volume = context.user_volume_accumulator;
    let user = context.user;
    let user_base_token_account = context.user_base_token_account;
    let user_quote_token_account = context.user_quote_token_account;
    let quote_with_lp_fee = result.quote_amount_in.checked_add(result.fees.lp_fee)
        .ok_or_else(|| error!(PumpAmmError::Overflow))?;
    let total_unclaimed_tokens = volume.total_unclaimed_tokens;
    let total_claimed_tokens = volume.total_claimed_tokens;
    let current_sol_volume = volume.current_sol_volume;
    let last_update_timestamp = volume.last_update_timestamp;
    let timestamp = Clock::get()?.unix_timestamp;
        let event = crate::trade::BuyEvent {
            timestamp,
            base_amount_out: result.base_amount_out,
            max_quote_amount_in,
            user_base_token_reserves: user_base_reserves,
            user_quote_token_reserves: user_quote_reserves,
            pool_base_token_reserves: b,
            pool_quote_token_reserves: raw_quote_reserves,
            quote_amount_in,
            lp_fee_basis_points: result.fees.lp_fee_bps,
            lp_fee: result.fees.lp_fee,
            protocol_fee_basis_points: result.fees.protocol_fee_bps,
            protocol_fee: result.fees.protocol_fee,
            quote_amount_in_with_lp_fee: quote_with_lp_fee,
            user_quote_amount_in,
            pool: pool.key(),
            user,
            user_base_token_account,
            user_quote_token_account,
            protocol_fee_recipient: Pubkey::default(),
            protocol_fee_recipient_token_account: Pubkey::default(),
            coin_creator: pool.coin_creator,
            coin_creator_fee_basis_points: result.fees.creator_fee_bps,
            coin_creator_fee: result.fees.creator_fee,
            holder_rewards_bps: if pool.is_holder_reward { result.fees.creator_fee_bps } else { 0 },
            holder_rewards: if pool.is_holder_reward { result.fees.creator_fee } else { 0 },
            track_volume: false,
            total_unclaimed_tokens,
            total_claimed_tokens,
            current_sol_volume,
            last_update_timestamp,
            min_base_amount_out,
            ix_name: ix_name.to_string(),
            cashback_fee_basis_points: 0,
            cashback: 0,
            buyback_fee_basis_points: if pool.is_mayhem_mode { 0 } else { global_config.buyback_basis_points },
            base_supply: if pool.is_mayhem_mode { 1_000_000_000_000_000 } else { base_supply },
            buyback_fee: buyback_received,
            virtual_quote_reserves: old_virtual,
            can_boost: pool.can_boost(),
            creator_fee_unclaimed: pool.creator_fees,
            quote_transfer_fee: result.quote_transfer_fee,
        };
    Ok(event)
}

/// Initial exact-input quote and its fee amounts, before buyback/transfer-fee preview.
#[inline(never)]
pub fn estimate_buy_quote(pool: &Pool, selected: &AppliedFees, available: u64) -> Result<(u64, AppliedFees)> {
    let creator_bps = if pool.coin_creator == Pubkey::default() { 0 } else { selected.creator_fee_bps };
    let fee_bps = selected.lp_fee_bps.saturating_add(selected.protocol_fee_bps).saturating_add(creator_bps);
    let estimate = if fee_bps == 0 { available } else {
        // The denominator is at least 10_000, so this quotient is <= available.
        ((available as u128) * 10_000 / ((fee_bps as u128) + 10_000)) as u64
    };
    require_gt!(estimate, 0, PumpAmmError::BuyNotEnoughQuoteTokensToCoverFees);
    let lp_fee = crate::curve::fees::fee(estimate, selected.lp_fee_bps)?;
    let protocol_fee = crate::curve::fees::fee(estimate, selected.protocol_fee_bps)?;
    let creator_fee = crate::curve::fees::fee(estimate, creator_bps)?;
    let required = total_quote(&[estimate, lp_fee, protocol_fee, creator_fee])?;
    let quote = estimate.checked_sub(required.saturating_sub(available))
        .ok_or(PumpAmmError::BuyNotEnoughQuoteTokensToCoverFees)?;
    require_gt!(quote, 0, PumpAmmError::BuySlippageBelowMinBaseAmountOut);
    Ok((quote, AppliedFees { lp_fee_bps: selected.lp_fee_bps, protocol_fee_bps: selected.protocol_fee_bps,
        creator_fee_bps: selected.creator_fee_bps, lp_fee, protocol_fee, creator_fee }))
}
