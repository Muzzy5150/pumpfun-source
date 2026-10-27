//! Partial PumpSwap reconstruction. Only explicitly implemented handlers exist.
//! This crate is not the historical source or a byte-identical replacement.
use anchor_lang::prelude::*;
mod state;
pub mod curve;
pub mod utils;
mod instructions;
use instructions::admin::create_config::*;
pub use instructions::token_incentives::init_user_volume_accumulator::InitUserVolumeAccumulator;
use instructions::token_incentives::*;
mod legacy_buy;
use legacy_buy::*;
mod legacy_sell;
use legacy_sell::*;
mod cashback;
use cashback::*;
mod incentives;
use incentives::*;
mod creator_reassignment;
use creator_reassignment::*;
mod multi_hop;
anchor_lang::declare_program!(pump);
anchor_lang::declare_program!(pump_fees);
mod trade;
mod create;
mod boost;
mod boost_burn;
pub mod sweep;
mod extend;
mod collect;
mod transfer_creator;
use anchor_spl::{token::Token, token_2022::Token2022, token_interface::{self, Mint, TokenAccount}};
pub use instructions::admin;
declare_id!("pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA");

#[program]
pub mod pump_amm_recovered {
    use super::*;
    // Static-only reconstruction: no authentic successful initializer replay exists.
    pub fn create_config(ctx: Context<CreateConfig>, lp_fee_basis_points: u64,
        protocol_fee_basis_points: u64, protocol_fee_recipients: [Pubkey; 8],
        coin_creator_fee_basis_points: u64, admin_set_coin_creator_authority: Pubkey) -> Result<()> {
        let admin = ctx.accounts.admin.key();
        let global_config = &mut ctx.accounts.global_config;
        global_config.admin = admin;
        global_config.set_lp_fee_basis_points(lp_fee_basis_points)?;
        global_config.set_protocol_fee_basis_points(protocol_fee_basis_points)?;
        global_config.set_protocol_fee_recipients(protocol_fee_recipients)?;
        global_config.set_coin_creator_fee_basis_points(coin_creator_fee_basis_points)?;
        global_config.disable_flags = 0;
        global_config.admin_set_coin_creator_authority = admin_set_coin_creator_authority;
        let event = CreateConfigEvent { timestamp: Clock::get()?.unix_timestamp,
            admin, lp_fee_basis_points, protocol_fee_basis_points,
            protocol_fee_recipients, coin_creator_fee_basis_points,
            admin_set_coin_creator_authority };
        emit!(event);
        emit_cpi!(event);
        Ok(())
    }

    pub fn disable(ctx: Context<AdminGlobal>, disable_create_pool: bool,
        disable_deposit: bool, disable_withdraw: bool,
        disable_buy: bool, disable_sell: bool) -> Result<()> {
        let flags = &mut ctx.accounts.global_config.disable_flags;
        *flags = (*flags & !1) | u8::from(disable_create_pool);
        *flags = (*flags & !2) | (u8::from(disable_deposit) << 1);
        *flags = (*flags & !4) | (u8::from(disable_withdraw) << 2);
        *flags = (*flags & !8) | (u8::from(disable_buy) << 3);
        *flags = (*flags & !16) | (u8::from(disable_sell) << 4);
        let event = DisableEvent { timestamp: Clock::get()?.unix_timestamp,
            admin: ctx.accounts.admin.key(), disable_create_pool,
            disable_deposit, disable_withdraw, disable_buy, disable_sell };
        emit!(event.clone());
        emit_cpi!(event);
        Ok(())
    }
    pub fn update_admin(ctx: Context<UpdateAdmin>) -> Result<()> {
        let admin = ctx.accounts.global_config.admin;
        let new_admin = ctx.accounts.new_admin.key();
        ctx.accounts.global_config.admin = new_admin;
        let event = UpdateAdminEvent { timestamp: Clock::get()?.unix_timestamp, admin, new_admin };
        emit!(event.clone());
        emit_cpi!(event);
        Ok(())
    }
    pub fn update_fee_config(ctx: Context<AdminGlobal>, lp_fee_basis_points: u64,
        protocol_fee_basis_points: u64, protocol_fee_recipients: [Pubkey; 8],
        coin_creator_fee_basis_points: u64, admin_set_coin_creator_authority: Pubkey) -> Result<()> {
        let config = &mut ctx.accounts.global_config;
        config.set_lp_fee_basis_points(lp_fee_basis_points)?;
        config.set_protocol_fee_basis_points(protocol_fee_basis_points)?;
        config.set_protocol_fee_recipients(protocol_fee_recipients)?;
        config.set_coin_creator_fee_basis_points(coin_creator_fee_basis_points)?;
        config.admin_set_coin_creator_authority = admin_set_coin_creator_authority;
        let event = UpdateFeeConfigEvent { timestamp: Clock::get()?.unix_timestamp,
            admin: ctx.accounts.admin.key(), lp_fee_basis_points, protocol_fee_basis_points,
            protocol_fee_recipients, coin_creator_fee_basis_points, admin_set_coin_creator_authority };
        emit!(event);
        emit_cpi!(event);
        Ok(())
    }
    pub fn update_creator_fee_config(ctx: Context<UpdateCreatorFeeConfig>, creator_fee_configurable: bool,
        max_configurable_creator_fee_bps: u64) -> Result<()> {
        let accounts = &mut *ctx.accounts;
        instructions::admin::extend_global_config(
            &accounts.global_config, &accounts.system_program, &accounts.admin,
        )?;
        accounts.global_config.creator_fee_configurable = creator_fee_configurable;
        accounts.global_config.max_configurable_creator_fee_bps = max_configurable_creator_fee_bps;
        let event = UpdateCreatorFeeConfigEvent { timestamp: Clock::get()?.unix_timestamp,
            admin: accounts.admin.key(), creator_fee_configurable, max_configurable_creator_fee_bps };
        emit!(event);
        emit_cpi!(event);
        Ok(())
    }
    pub fn create_pool(ctx: Context<CreatePool>, index: u16, base_amount_in: u64, quote_amount_in: u64, coin_creator: Pubkey, is_mayhem_mode: bool, is_cashback_coin: OptionBool, creator_fee_bps: OptionU64, can_edit_creator_fee: OptionBool, is_holder_reward: OptionBool) -> Result<()> { create::execute(ctx,index,base_amount_in,quote_amount_in,coin_creator,is_mayhem_mode,is_cashback_coin.0,creator_fee_bps.0,can_edit_creator_fee.0,is_holder_reward.0) }
    pub fn init_boost(ctx: Context<InitBoost>) -> Result<()> { boost::execute(ctx) }
    pub fn set_boost_authority(ctx: Context<SetBoostAuthority>) -> Result<()> {
        let accounts = &mut *ctx.accounts;
        instructions::admin::extend_global_config(
            &accounts.global_config, &accounts.system_program, &accounts.admin,
        )?;
        let old_boost_authority = accounts.global_config.boost_authority;
        let new_boost_authority = accounts.boost_authority.key();
        accounts.global_config.boost_authority = new_boost_authority;
        let event = SetBoostAuthorityEvent { timestamp: Clock::get()?.unix_timestamp,
            admin: accounts.admin.key(), old_boost_authority, new_boost_authority };
        emit!(event);
        emit_cpi!(event);
        Ok(())
    }
    pub fn boost_buy_and_burn(ctx: Context<BoostBuyAndBurn>, quote_amount_in: u64, min_base_amount_burned: u64) -> Result<()> { boost_burn::execute(ctx, quote_amount_in, min_base_amount_burned) }
    pub fn set_reserved_fee_recipients(ctx: Context<SetReservedFeeRecipients>, whitelist_pda: Pubkey) -> Result<()> {
        require!(ctx.remaining_accounts.len() >= 8, PumpAmmError::NotEnoughRemainingAccounts);
        let mut recipients = [Pubkey::default(); 8];
        for i in 0..8 {
            recipients[i] = ctx.remaining_accounts[i].key();
            require_keys_neq!(recipients[i], Pubkey::default(), PumpAmmError::AllProtocolFeeRecipientsShouldBeNonZero);
        }
        ctx.accounts.global_config.whitelist_pda = whitelist_pda;
        ctx.accounts.global_config.reserved_fee_recipient = recipients[0];
        ctx.accounts.global_config.reserved_fee_recipients.copy_from_slice(&recipients[1..]);
        let event = ReservedFeeRecipientsEvent { timestamp: Clock::get()?.unix_timestamp,
            reserved_fee_recipient: recipients[0], reserved_fee_recipients: recipients[1..].try_into().unwrap() };
        emit!(event.clone());
        emit_cpi!(event);
        Ok(())
    }
    pub fn deposit(ctx: Context<Liquidity>, lp_token_amount_out: u64, max_base_amount_in: u64, max_quote_amount_in: u64) -> Result<()> {
        instructions::liquidity::deposit::deposit(ctx, lp_token_amount_out, max_base_amount_in, max_quote_amount_in)
    }
    pub fn withdraw(ctx: Context<Liquidity>, lp_token_amount_in: u64, min_base_amount_out: u64, min_quote_amount_out: u64) -> Result<()> {
        instructions::liquidity::withdraw::withdraw(ctx, lp_token_amount_in, min_base_amount_out, min_quote_amount_out)
    }

    pub fn admin_update_token_incentives(ctx:Context<AdminUpdateTokenIncentives>,start_time:i64,end_time:i64,seconds_in_a_day:i64,day_number:u64,token_supply_per_day:u64)->Result<()>{incentives::admin(ctx,start_time,end_time,seconds_in_a_day,day_number,token_supply_per_day)}
    pub fn claim_token_incentives(ctx:Context<ClaimTokenIncentives>)->Result<()>{incentives::claim(ctx)}

    pub fn init_user_volume_accumulator(ctx: Context<InitUserVolumeAccumulator>) -> Result<()> {
        let event = InitUserVolumeAccumulatorEvent { payer: ctx.accounts.payer.key(),
            user: ctx.accounts.user.key(), timestamp: Clock::get()?.unix_timestamp };
        ctx.accounts.user_volume_accumulator.user = ctx.accounts.user.key();
        emit!(event.clone());
        emit_cpi!(event);
        Ok(())
    }

    pub fn close_user_volume_accumulator(ctx: Context<CloseUserVolumeAccumulator>) -> Result<()> {
        let account = &ctx.accounts.user_volume_accumulator;
        let event = CloseUserVolumeAccumulatorEvent { user: ctx.accounts.user.key(),
            timestamp: Clock::get()?.unix_timestamp, total_unclaimed_tokens: account.total_unclaimed_tokens,
            total_claimed_tokens: account.total_claimed_tokens, current_sol_volume: account.current_sol_volume,
            last_update_timestamp: account.last_update_timestamp };
        emit!(event.clone());
        emit_cpi!(event);
        Ok(())
    }

    pub fn sync_user_volume_accumulator(ctx:Context<SyncUserVolumeAccumulator>)->Result<()>{incentives::sync(ctx)}
    pub fn buy<'info>(ctx:Context<'_,'_,'_,'info,LegacyBuy<'info>>,base_amount_out:u64,max_quote_amount_in:u64,track_volume:OptionBool)->Result<()>{legacy_buy::execute(ctx,base_amount_out,max_quote_amount_in,track_volume.0,false)}

    pub fn buy_exact_quote_in<'info>(ctx:Context<'_,'_,'_,'info,LegacyBuy<'info>>,spendable_quote_in:u64,min_base_amount_out:u64,track_volume:OptionBool)->Result<()>{legacy_buy::execute(ctx,spendable_quote_in,min_base_amount_out,track_volume.0,true)}
    pub fn sell<'info>(ctx:Context<'_,'_,'_,'info,LegacySell<'info>>,base_amount_in:u64,min_quote_amount_out:u64)->Result<()>{legacy_sell::execute(ctx,base_amount_in,min_quote_amount_out)}

    pub fn buy_v2(ctx: Context<TradeV2>, base_amount_out: u64, max_quote_amount_in: u64) -> Result<()> { trade::execute_buy(ctx, base_amount_out, max_quote_amount_in) }

    pub fn buy_exact_quote_in_v2(ctx: Context<TradeV2>, spendable_quote_in: u64, min_base_amount_out: u64) -> Result<()> { trade::execute_buy_exact_quote(ctx, spendable_quote_in, min_base_amount_out) }
    pub fn sell_v2(ctx: Context<TradeV2>, base_amount_in: u64, min_quote_amount_out: u64) -> Result<()> { trade::execute_sell(ctx, base_amount_in, min_quote_amount_out) }
    pub fn multi_hop_swap<'info>(ctx:Context<'_, '_, 'info, 'info, MultiHop<'info>>,amount_in:u64,min_amount_out:u64)->Result<()>{multi_hop::execute(ctx,amount_in,min_amount_out)}
    pub fn sweep_protocol_fee(ctx: Context<SweepFees>) -> Result<()> { sweep::execute(ctx,false) }
    pub fn sweep_creator_fee(ctx: Context<SweepFees>) -> Result<()> { sweep::execute(ctx,true) }

    pub fn extend_account(ctx: Context<ExtendAccount>) -> Result<()> { extend::execute(ctx) }
    pub fn collect_coin_creator_fee(ctx: Context<CollectCoinCreatorFee>) -> Result<()> { collect::execute(ctx) }

    pub fn set_coin_creator(ctx:Context<SetCoinCreator>)->Result<()>{creator_reassignment::set(ctx)}

    pub fn admin_cto_pool(ctx:Context<AdminCtoPool>,coin_creator:Pubkey,is_holder_reward:bool,creator_fee_bps:Option<u64>)->Result<()>{creator_reassignment::admin_cto(ctx,coin_creator,is_holder_reward,creator_fee_bps)}

    pub fn toggle_mayhem_mode(ctx: Context<AdminGlobal>, enabled: bool) -> Result<()> {
        require_neq!(ctx.accounts.global_config.mayhem_mode_enabled, enabled, PumpAmmError::MayhemModeInDesiredState);
        ctx.accounts.global_config.mayhem_mode_enabled = enabled;
        Ok(())
    }

    pub fn toggle_boost(ctx: Context<AdminGlobalNoEvent>, enabled: bool) -> Result<()> {
        require_keys_neq!(ctx.accounts.global_config.boost_authority, Pubkey::default(), PumpAmmError::InvalidAdmin);
        ctx.accounts.global_config.boost_enabled = enabled;
        Ok(())
    }

    pub fn transfer_creator_fees_to_pump(ctx: Context<TransferCreatorFeesToPump>) -> Result<()> { transfer_creator::legacy(ctx) }

    pub fn transfer_creator_fees_to_pump_v2(ctx: Context<TransferCreatorFeesToPumpV2>) -> Result<()> { transfer_creator::v2(ctx) }
    pub fn migrate_pool_coin_creator(ctx:Context<MigratePoolCoinCreator>)->Result<()>{creator_reassignment::migrate(ctx)}
    pub fn toggle_cashback_enabled(ctx: Context<AdminGlobal>, enabled: bool) -> Result<()> {
        require_neq!(ctx.accounts.global_config.is_cashback_enabled, enabled, PumpAmmError::CashbackNotInDesiredState);
        ctx.accounts.global_config.is_cashback_enabled = enabled;
        Ok(())
    }

    pub fn claim_cashback(ctx:Context<ClaimCashback>)->Result<()>{cashback::claim(ctx)}

    pub fn update_buyback_config(ctx: Context<AdminGlobal>, buyback_basis_points: Option<u64>) -> Result<()> {
        let accounts = &mut *ctx.accounts;
        if let Some(bps) = buyback_basis_points {
            accounts.global_config.set_buyback_basis_points(bps)?;
        }
        if !ctx.remaining_accounts.is_empty() {
            require!(ctx.remaining_accounts.len() == 8, PumpAmmError::WrongBuybackFeeRecipientsCount);
            let mut recipients = [Pubkey::default(); 8];
            for (i, account) in ctx.remaining_accounts.iter().enumerate() { recipients[i] = account.key(); }
            accounts.global_config.set_buyback_fee_recipients(recipients)?;
        }
        Ok(())
    }
}
use transfer_creator::*;
use collect::*;
use extend::*;
use sweep::*;
use boost::*;
use boost_burn::*;
use create::*;
use trade::*;
use {multi_hop::*, state::*};

#[event_cpi]
#[derive(Accounts)]
pub struct AdminGlobal<'info> {
    pub admin: Signer<'info>,
    #[account(mut, has_one = admin @ PumpAmmError::InvalidAdmin)]
    pub global_config: Box<Account<'info, GlobalConfig>>,
}

#[error_code]
pub enum PumpAmmError {
    FeeBasisPointsExceedsMaximum = 0,
    ZeroBaseAmount = 1,
    ZeroQuoteAmount = 2,
    TooLittlePoolTokenLiquidity = 3,
    ExceededSlippage = 4,
    InvalidAdmin = 5,
    UnsupportedBaseMint = 6,
    UnsupportedQuoteMint = 7,
    InvalidBaseMint = 8,
    InvalidQuoteMint = 9,
    InvalidLpMint = 10,
    AllProtocolFeeRecipientsShouldBeNonZero = 11,
    UnsortedNotUniqueProtocolFeeRecipients = 12,
    InvalidProtocolFeeRecipient = 13,
    InvalidPoolBaseTokenAccount = 14,
    InvalidPoolQuoteTokenAccount = 15,
    BuyMoreBaseAmountThanPoolReserves = 16,
    DisabledCreatePool = 17,
    DisabledDeposit = 18,
    DisabledWithdraw = 19,
    DisabledBuy = 20,
    DisabledSell = 21,
    SameMint = 22,
    Overflow = 23,
    Truncation = 24,
    DivisionByZero = 25,
    NewSizeLessThanCurrentSize = 26,
    AccountTypeNotSupported = 27,
    OnlyCanonicalPumpPoolsCanHaveCoinCreator = 28,
    InvalidAdminSetCoinCreatorAuthority = 29,
    StartTimeInThePast = 30,
    EndTimeInThePast = 31,
    EndTimeBeforeStartTime = 32,
    TimeRangeTooLarge = 33,
    EndTimeBeforeCurrentDay = 34,
    SupplyUpdateForFinishedRange = 35,
    DayIndexAfterEndIndex = 36,
    DayInActiveRange = 37,
    InvalidIncentiveMint = 38,
    #[msg("buy: Not enough quote tokens to cover for fees.")]
    BuyNotEnoughQuoteTokensToCoverFees = 39,
    #[msg("buy: slippage - would buy less tokens than expected min_base_amount_out")]
    BuySlippageBelowMinBaseAmountOut = 40,
    MayhemModeDisabled = 41,
    OnlyPumpPoolsMayhemMode = 42,
    MayhemModeInDesiredState = 43,
    NotEnoughRemainingAccounts = 44,
    InvalidSharingConfigBaseMint = 45,
    InvalidSharingConfigCoinCreator = 46,
    #[msg("coin creator has been migrated to sharing config")]
    CoinCreatorMigratedToSharingConfig = 47,
    #[msg("creator_vault has been migrated to sharing config, use pump:distribute_creator_fees instead")]
    CreatorVaultMigratedToSharingConfig = 48,
    #[msg("Cashback is disabled")]
    CashbackNotEnabled = 49,
    OnlyPumpPoolsCashback = 50,
    CashbackNotInDesiredState = 51,
    TokensInVaultLessThanCashbackEarned = 52,
    #[msg("Buyback fee recipient not authorized")]
    BuybackFeeRecipientNotAuthorized = 53,
    AllBuybackFeeRecipientsShouldBeNonZero = 54,
    NotUniqueBuybackFeeRecipients = 55,
    #[msg("buyback_basis_points must be <= 10_000")]
    BuybackBasisPointsOutOfRange = 56,
    #[msg("buyback fee recipients require exactly 8 remaining accounts (or none)")]
    WrongBuybackFeeRecipientsCount = 57,
    BuybackFeeRecipientMissing = 58,
    #[msg("Cashback trade is missing the required remaining accounts")]
    MissingCashbackAccounts = 59,
    #[msg("Cashback user_volume_accumulator account is invalid")]
    InvalidCashbackAccumulator = 60,
    #[msg("Cashback user_volume_accumulator ATA is missing or invalid")]
    InvalidCashbackAccumulatorAta = 61,
    #[msg("pool_v2 remaining account is missing or invalid")]
    InvalidPoolV2 = 62,
    #[msg("BOOST: sell output exceeds the real quote vault. effective = real + virtual is pricing-only; payout is capped at real_vault, so quote min(out, real_vault)")]
    InsufficientRealQuoteReserves = 63,
    #[msg("BOOST: deposit/withdraw don't apply to boost pools")]
    BoostPoolLiquidityUnsupported = 64,
    #[msg("BOOST: pool cannot be boosted (no virtual reserves)")]
    PoolCannotBoost = 65,
    #[msg("BOOST: boost is disabled")]
    BoostDisabled = 66,
    #[msg("BOOST: lp_supply must never drop below the circulating LP mint supply")]
    SeedLockViolation = 67,
    #[msg("Configurable creator fee is disabled")]
    CreatorFeeNotConfigurable = 68,
    #[msg("Creator fee basis points must be between 1 and the configured maximum")]
    CreatorFeeBpsOutOfRange = 69,
    #[msg("Creator fee is not editable for this pool")]
    CreatorFeeNotEditable = 70,
    #[msg("Cashback coins cannot have a creator fee")]
    CreatorFeeNotAllowedForCashbackCoin = 71,
    #[msg("Sharing config is not active")]
    SharingConfigNotActive = 72,
    #[msg("Not authorized")]
    NotAuthorized = 73,
    #[msg("The coin creator of a holder-reward pool cannot be changed")]
    HolderRewardCreatorImmutable = 74,
    #[msg("CTO is not allowed on a mayhem-mode pool")]
    CtoNotAllowedForMayhemPool = 75,
    #[msg("A holder-reward pool's coin creator must be the holder-rewards PDA")]
    InvalidHolderRewardCoinCreator = 76,
    #[msg("Creator fee is not configurable on a SOL or USDC quote; the fee schedule applies")]
    CreatorFeeNotConfigurableForQuote = 77,
    #[msg("Only canonical pump pools are supported by this instruction")]
    OnlyPumpPools = 78,
    #[msg("v2 trades do not support cashback coins; use the v1 instructions")]
    CashbackCoinNotSupported = 79,
    #[msg("v2 trades do not support mayhem-mode pools; use the v1 instructions")]
    MayhemPoolNotSupported = 80,
    #[msg("creator_fees must be swept before the coin creator changes")]
    CreatorFeesNotSwept = 81,
    #[msg("The fee config tier table is empty")]
    FeeTiersEmpty = 82,
    #[msg("The fee config account is shorter than its initialize size")]
    FeeConfigTooShort = 83,
    #[msg("multi-hop: a hop's input mint is neither side of its pool or curve, or the route does not end in user_out_token_account's mint")]
    MultiHopDiscontinuousPath = 84,
    #[msg("multi-hop: the balances around the bonding-curve hops do not match the amounts pump reported")]
    MultiHopCurveRunMismatch = 85,
    #[msg("multi-hop: every hop must trade in the same direction, all buys or all sells")]
    MultiHopMixedDirection = 86,
    #[msg("A transfer's source is its destination and the signer does not own it")]
    SelfTransferNotAllowed = 87,
    #[msg("quote_mint must be writable for a quote with a Token-2022 transfer fee: its withheld fees are harvested to the mint")]
    QuoteMintNotWritable = 88,
}

#[event_cpi]
#[derive(Accounts)]
pub struct UpdateAdmin<'info> {
    pub admin: Signer<'info>,
    #[account(mut, has_one = admin @ PumpAmmError::InvalidAdmin)]
    pub global_config: Box<Account<'info, GlobalConfig>>,
    /// CHECK: Only this account's public key is stored as the new admin.
    pub new_admin: AccountInfo<'info>,
}

#[derive(Accounts)]
pub struct AdminGlobalNoEvent<'info> {
    pub admin: Signer<'info>,
    #[account(mut, has_one = admin @ PumpAmmError::InvalidAdmin)]
    pub global_config: Box<Account<'info, GlobalConfig>>,
}

#[event_cpi]
#[derive(Accounts)]
pub struct SetBoostAuthority<'info> {
    pub admin: Signer<'info>,
    #[account(mut, has_one = admin @ PumpAmmError::InvalidAdmin)]
    pub global_config: Box<Account<'info, GlobalConfig>>,
    /// CHECK: Only its public key is stored as authority.
    pub boost_authority: AccountInfo<'info>,
    pub system_program: Program<'info, System>,
}

#[event_cpi]
#[derive(Accounts)]
pub struct UpdateCreatorFeeConfig<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,
    #[account(mut, has_one = admin @ PumpAmmError::InvalidAdmin)]
    pub global_config: Box<Account<'info, GlobalConfig>>,
    pub system_program: Program<'info, System>,
}

#[event_cpi]
#[derive(Accounts)]
pub struct SetReservedFeeRecipients<'info> {
    #[account(mut, seeds = [b"global_config"], bump, has_one = admin @ PumpAmmError::InvalidAdmin)]
    pub global_config: Account<'info, GlobalConfig>,
    pub admin: Signer<'info>,
}

#[event_cpi]
#[derive(Accounts)]
pub struct CloseUserVolumeAccumulator<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mut, close = user, seeds = [b"user_volume_accumulator", user.key().as_ref()], bump)]
    pub user_volume_accumulator: Account<'info, UserVolumeAccumulator>,
}

#[event_cpi]
#[derive(Accounts)]
pub struct Liquidity<'info> {
    #[account(mut, has_one = base_mint @ PumpAmmError::InvalidBaseMint, has_one = quote_mint @ PumpAmmError::InvalidQuoteMint, has_one = lp_mint @ PumpAmmError::InvalidLpMint, has_one = pool_base_token_account @ PumpAmmError::InvalidPoolBaseTokenAccount, has_one = pool_quote_token_account @ PumpAmmError::InvalidPoolQuoteTokenAccount)]
    pub pool: Box<Account<'info, Pool>>,
    pub global_config: Box<Account<'info, GlobalConfig>>,
    pub user: Signer<'info>,
    pub base_mint: Box<InterfaceAccount<'info, Mint>>,
    pub quote_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(mut)]
    pub lp_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(mut)]
    pub user_base_token_account: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut)]
    pub user_quote_token_account: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, token::authority = user)]
    pub user_pool_token_account: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut)]
    pub pool_base_token_account: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut)]
    pub pool_quote_token_account: Box<InterfaceAccount<'info, TokenAccount>>,
    pub token_program: Program<'info, Token>,
    pub token_2022_program: Program<'info, Token2022>,
}
fn liquidity_total_fees(pool: &Pool) -> Result<u64> {
    pool.total_accrued_fees()
}
fn liquidity_quote_reserves(pool: &Pool, quote_token_amount: u64) -> Result<u64> {
    pool.available_quote_reserves(quote_token_amount)
}
fn liquidity_effective_virtual(pool: &Pool) -> Result<i128> {
    pool.total_virtual_quote_reserves()
}


fn quote_transfer_fee(mint: &AccountInfo, amount: u64, inverse: bool) -> Result<u64> {
    let fee = crate::utils::transfer_fee::from_mint(mint)?;
    let pre_fee_amount = if inverse {
        crate::utils::transfer_fee::amount_before_fee(&fee, amount)?
    } else {
        amount
    };
    crate::utils::transfer_fee::calculate_fee(&fee, pre_fee_amount)
}

pub use trade::{execute_buy, execute_buy_exact_quote, execute_sell};
