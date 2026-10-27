use crate::*;
#[event_cpi]
#[derive(Accounts)]
pub struct AdminSetIdlAuthority<'info> {
    pub authority: Signer<'info>,
    #[account(seeds=[b"global"],bump,has_one=authority @ PumpError::NotAuthorized)]
    pub global: Account<'info,Global>,
    /// CHECK: canonical Anchor IDL account, checked and resized by the handler.
    #[account(mut,address=anchor_lang::idl::IdlAccount::address(&crate::ID))]
    pub idl_account: AccountInfo<'info>,
    pub system_program: Program<'info,System>,
    /// CHECK: the program signs its own canonical empty-seed PDA.
    #[account(seeds=[],bump)]
    pub program_signer: AccountInfo<'info>,
}
pub fn execute(ctx:Context<AdminSetIdlAuthority>,idl_authority:Pubkey)->Result<()> {
    let account=ctx.accounts.idl_account.to_account_info();
    if account.owner==&anchor_lang::system_program::ID {
        let cpi_accounts=anchor_lang::system_program::TransferWithSeed{
            from:account.clone(),base:ctx.accounts.program_signer.to_account_info(),
            to:ctx.accounts.authority.to_account_info()};
        let signer_seeds:&[&[&[u8]]]=&[&[&[ctx.bumps.program_signer]]];
        let cpi_context=CpiContext::new_with_signer(ctx.accounts.system_program.to_account_info(),cpi_accounts,signer_seeds);
        anchor_lang::system_program::transfer_with_seed(
            cpi_context,String::from("anchor:idl"),&crate::ID,account.lamports())?;
        return Ok(());
    } else {
        require!(account.owner==&crate::ID,PumpError::AccountTypeNotSupported);
        account.realloc(10240,false)?;
        require!(account.try_borrow_data()?[..8]==[24,70,98,191,58,144,123,158],PumpError::AccountTypeNotSupported);
    }
    let mut header=anchor_lang::idl::IdlAccount::try_deserialize(&mut &account.try_borrow_data()?[..])?;
    header.authority=idl_authority;
    header.try_serialize(&mut &mut account.try_borrow_mut_data()?[..])?;
    let event=AdminSetIdlAuthorityEvent{idl_authority};emit!(event.clone());emit_cpi!(event);Ok(())
}
#[event]
#[derive(Clone)]
pub struct AdminSetIdlAuthorityEvent {pub idl_authority:Pubkey}
