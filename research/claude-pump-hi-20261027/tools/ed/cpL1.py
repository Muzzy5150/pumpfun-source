CALL1=' create_pool(&ctx,base,'
CALL2='  quote)?;'
ACC="pump_amm::cpi::accounts::CreatePool{pool:a.pool.to_account_info(),global_config:a.amm_global_config.to_account_info(),creator:a.pool_authority.to_account_info(),base_mint:a.base_mint.to_account_info(),quote_mint:a.quote_mint.to_account_info(),lp_mint:a.lp_mint.to_account_info(),user_base_token_account:a.pool_authority_mint_account.to_account_info(),user_quote_token_account:a.pool_authority_quote_account.to_account_info(),user_pool_token_account:a.user_pool_token_account.to_account_info(),pool_base_token_account:a.pool_base_token_account.to_account_info(),pool_quote_token_account:a.pool_quote_token_account.to_account_info(),system_program:a.system_program.to_account_info(),token_2022_program:a.token_2022_program.to_account_info(),base_token_program:a.base_token_program.to_account_info(),quote_token_program:a.quote_token_program.to_account_info(),associated_token_program:a.associated_token_program.to_account_info(),event_authority:a.pump_amm_event_authority.to_account_info(),program:a.pump_amm.to_account_info()}"
ARGS="0,base,quote,a.bonding_curve.creator,a.bonding_curve.is_mayhem_mode,pump_amm::types::OptionBool(a.bonding_curve.is_cashback_coin),pump_amm::types::OptionU64(a.bonding_curve.creator_fee_bps),pump_amm::types::OptionBool(a.bonding_curve.can_edit_creator_fee),pump_amm::types::OptionBool(a.bonding_curve.is_holder_reward)"
HELPER='''
// Original: standalone pool-creation helper (window 0x502f0) calling the generated pump_amm client.
#[inline(never)]
pub fn create_pool<'info>(ctx:&Context<'_,'_,'_,'info,MigrateV2<'info>>,base:u64,quote:u64)->Result<()>{
 let bump=ctx.bumps.pool_authority;let a=&ctx.accounts;let mint=a.base_mint.key();
 let signer:&[&[&[u8]]]=&[&[b"pool-authority",mint.as_ref(),&[bump]]];
 pump_amm::cpi::create_pool(CpiContext::new_with_signer(a.pump_amm.to_account_info(),ACC,signer),ARGS)
}'''.replace('ACC',ACC).replace('ARGS',ARGS)
exec(open('/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/pump-hi/mini/ed/cp_common.py').read())
