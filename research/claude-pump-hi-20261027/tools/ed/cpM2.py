# v2 helper (0x502f0) as matched in cpL6c
exec(open('/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/pump-hi/mini/ed/cpL6c.py').read())
# v1 helper (0x43ea0)
f='migrate.rs'
n0=lines(f)
s=(src/f).read_text().split('\n')
i=[k for k,l in enumerate(s) if l.startswith(' let creator=a.bonding_curve.creator;let cpi_accounts=pump_amm::cpi::accounts::CreatePool{')]
assert len(i)==1; i=i[0]
assert s[i+1].startswith(' pump_amm::cpi::create_pool(CpiContext::new_with_signer(am.clone(),cpi_accounts,&[pas]),0,base,quote,creator,mayhem,')
s[i]=' create_pool(&ctx,base,'; s[i+1]='  quote)?;'
ACC1="pump_amm::cpi::accounts::CreatePool{pool:a.pool.to_account_info(),global_config:a.amm_global_config.to_account_info(),creator:a.pool_authority.to_account_info(),base_mint:a.mint.to_account_info(),quote_mint:a.wsol_mint.to_account_info(),lp_mint:a.lp_mint.to_account_info(),user_base_token_account:a.pool_authority_mint_account.to_account_info(),user_quote_token_account:a.pool_authority_wsol_account.to_account_info(),user_pool_token_account:a.user_pool_token_account.to_account_info(),pool_base_token_account:a.pool_base_token_account.to_account_info(),pool_quote_token_account:a.pool_quote_token_account.to_account_info(),system_program:a.system_program.to_account_info(),token_2022_program:a.token_2022_program.to_account_info(),base_token_program:base_token_program(a.mint.as_ref().as_ref(),&a.token_program,&a.token_2022_program),quote_token_program:a.token_program.to_account_info(),associated_token_program:a.associated_token_program.to_account_info(),event_authority:a.pump_amm_event_authority.to_account_info(),program:a.pump_amm.to_account_info()}"
ARGS1="0,base,quote,a.bonding_curve.creator,a.bonding_curve.is_mayhem_mode,pump_amm::types::OptionBool(a.bonding_curve.is_cashback_coin),pump_amm::types::OptionU64(a.bonding_curve.creator_fee_bps),pump_amm::types::OptionBool(a.bonding_curve.can_edit_creator_fee),pump_amm::types::OptionBool(a.bonding_curve.is_holder_reward)"
HELPER1='''
// Original: standalone pool-creation helper (window 0x43ea0) calling the generated pump_amm client.
fn create_pool<'info>(ctx:&Context<'_,'_,'_,'info,Migrate<'info>>,base:u64,quote:u64)->Result<()>{
 let bump=ctx.bumps.pool_authority;let a=&ctx.accounts;
 let create=move |signer_seeds:&[&[&[u8]];1]|pump_amm::cpi::create_pool(CpiContext::new_with_signer(a.pump_amm.to_account_info(),ACC1,signer_seeds),ARGS1);
 create(&[&[b"pool-authority",a.mint.key().as_ref(),&[bump]]])
}

// Original: the base mint's token program, chosen by the mint owner (window 0x47e28).
#[inline(never)]
fn base_token_program<'info>(mint:&AccountInfo<'info>,token_program:&AccountInfo<'info>,token_2022_program:&AccountInfo<'info>)->AccountInfo<'info>{
 if *mint.to_account_info().owner==anchor_spl::token::ID{token_program.to_account_info()}else{token_2022_program.to_account_info()}
}'''.replace('ACC1',ACC1).replace('ARGS1',ARGS1)
(src/f).write_text('\n'.join(s).rstrip('\n')+'\n'+HELPER1+'\n')
