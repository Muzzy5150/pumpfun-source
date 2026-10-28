exec(open('/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/pump-hi/mini/ed/cpL1.py').read().split('HELPER=')[0])
HELPER='''
// Original: standalone pool-creation helper (window 0x502f0) calling the generated pump_amm client.
#[inline(never)]
pub fn create_pool<'info>(ctx:&Context<'_,'_,'_,'info,MigrateV2<'info>>,base:u64,quote:u64)->Result<()>{
 let bump=ctx.bumps.pool_authority;let a=&ctx.accounts;
 let create=move |signer_seeds:&[&[&[u8]];1]|pump_amm::cpi::create_pool(CpiContext::new_with_signer(a.pump_amm.to_account_info(),ACC,signer_seeds),ARGS);
 create(&[&[b"pool-authority",a.base_mint.key().as_ref(),&[bump]]])
}'''.replace('ACC',ACC).replace('ARGS',ARGS)
exec(open('/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/pump-hi/mini/ed/cp_common.py').read())
