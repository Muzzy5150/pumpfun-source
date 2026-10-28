use super::*;

pub fn sync(mut ctx:Context<SetMetaplexCreator>)->Result<()>{let a=&mut ctx.accounts;if a.bonding_curve.creator!=Pubkey::default(){msg!("Bonding curve has creator already set");return Ok(());}match &a.metadata.creators{Some(cs)=>{let creator=cs[0].address;a.bonding_curve.creator=creator;let e=SetMetaplexCreatorEvent{timestamp:Clock::get()?.unix_timestamp,mint:a.mint.key(),bonding_curve:a.bonding_curve.key(),metadata:a.metadata.key(),creator};emit!(e);emit_cpi!(e);return Ok(());}None=>{msg!("Missing metaplex creators");}}Ok(())}
