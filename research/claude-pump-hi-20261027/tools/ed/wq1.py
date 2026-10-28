exec(open('/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/pump-hi/mini/ed/cpM2.py').read())
f='migrate.rs'
s=(src/f).read_text().split('\n')
i=[k for k,l in enumerate(s) if l==' move_lamports(&curve,&tmpq,quote)?;']
assert len(i)==1; i=i[0]
assert s[i+1].startswith(' call(&tok,&[(&tmpq,false,true),(&a.rent.to_account_info(),false,false),(&curve,false,false)],vec![17],&[])?;')
s[i]=' fund_quote(a,'; s[i+1]='  quote)?;'
HELPER2='''
// Original: moves the migration quote from the curve into the pool authority's WSOL account, then syncs it (window 0x43060).
fn fund_quote(a:&Migrate,amount:u64)->Result<()>{
 a.bonding_curve.sub_lamports(amount)?;
 a.pool_authority_wsol_account.add_lamports(amount)?;
 anchor_lang::solana_program::program::invoke(&Instruction{program_id:anchor_spl::token::ID,accounts:vec![AccountMeta::new(a.pool_authority_wsol_account.key(),false),AccountMeta::new_readonly(a.rent.key(),false),AccountMeta::new(a.bonding_curve.key(),false)],data:anchor_spl::token::spl_token::instruction::TokenInstruction::SyncNative.pack()},&[a.pool_authority_wsol_account.to_account_info(),a.rent.to_account_info(),a.bonding_curve.to_account_info()])?;
 Ok(())
}'''
(src/f).write_text('\n'.join(s).rstrip('\n')+'\n'+HELPER2+'\n')
