from pathlib import Path
ACC = ['global:a.global.as_ref()','mint:a.mint.as_ref().as_ref()','quote_mint:a.quote_mint.as_ref()','token_program:a.token_program.as_ref()',
 'quote_token_program:a.quote_token_program.as_ref()','associated_token_program:a.associated_token_program.as_ref()','fee_recipient:a.fee_recipient.as_ref()',
 'fee_recipient_ata:a.fee_recipient_ata.as_ref()','buyback_recipient:a.buyback_recipient.as_ref()','buyback_recipient_ata:a.buyback_recipient_ata.as_ref()',
 'bonding_curve:a.bonding_curve.as_ref().as_ref()','associated_bonding_curve:a.associated_base_bonding_curve.as_ref().as_ref()',
 'associated_quote_bonding_curve:a.associated_quote_bonding_curve.as_ref()','user:a.sol_vault.as_ref()','associated_user:a.mayhem_base_token_vault.as_ref().as_ref()',
 'associated_quote_user:a.mayhem_quote_token_vault.as_ref().as_ref()','creator_vault:a.creator_vault.as_ref()','associated_creator_vault:a.associated_creator_vault.as_ref()',
 'sharing_config:a.sharing_config.as_ref()','global_volume_accumulator:a.global_volume_accumulator.as_ref()','user_volume_accumulator:a.user_volume_accumulator.as_ref()',
 'associated_user_volume_accumulator:a.associated_user_volume_accumulator.as_ref()','fee_config:a.fee_config.as_ref()','fee_program:a.fee_program.as_ref()',
 'system_program:a.system_program.as_ref()','event_authority:a.pump_event_authority.as_ref()','program:a.pump_program.as_ref()']
def edit(root):
    bv = root/'src/instructions/buy_v2.rs'; s = bv.read_text()
    i = s.index('fn math()->Error'); j = s.index('pub fn handler(ctx:Context<BuyV2>')
    k = s.index('\n let event=SellEvent{side:0', j); event = s[k+1:s.index('\n', k+1)]
    assert s.rstrip().endswith('}')
    bv.write_text(s[:i])                       # keep the accounts struct and imports only
    accounts = ','.join(f'{f.split(":",1)[0]}:inline_cpi_info({f.split(":",1)[1]})' for f in ACC)
    h = [
     "pub fn buy_v2_handler(ctx:Context<BuyV2>,reference:u128,tolerance_bps:u16,retained_reserve_bps:u16)->Result<()> {",
     " let a=&mut *ctx.accounts;",
     " a.mayhem_state.validate_trade(&a.global_params)?;",
     " a.mayhem_state.validate_quote(a.bonding_curve.real_sol_reserves,&a.global_params,&a.quote_mint.key())?;",
     " let c=&a.bonding_curve;",
     " let price_check:std::result::Result<(),MayhemError> = (|| {",
     " let vt=c.virtual_token_reserves as u128;if vt==0{return Err(MayhemError::MathOverflow);}",
     " let scaled=reference.checked_mul(tolerance_bps as u128);",
     " let vs=c.virtual_sol_reserves as u128;let price=vs*1_000_000_000_000_000u128/vt;",
     " let delta=scaled.ok_or(MayhemError::MathOverflow)?/10_000;",
     " let low=reference.checked_sub(delta).ok_or(MayhemError::MathOverflow)?;",
     " let high=reference.checked_add(delta).ok_or(MayhemError::MathOverflow)?;",
     " if price<low||price>high{return Err(MayhemError::PumpCpiSlippage);}",
     " Ok(())",
     " })();price_check?;let vt=c.virtual_token_reserves as u128;let vs=c.virtual_sol_reserves as u128;",
     " let retained=crate::state::retained_basis_points(retained_reserve_bps);",
     " let native_accounting=a.quote_mint.key()==Pubkey::default()||a.quote_mint.key()==anchor_spl::token::spl_token::native_mint::id();",
     " let cap=if native_accounting{a.global_params.field_2}else{a.global_params.field_11};",
     " let (input,output)=crate::state::buy_amounts(vt,vs,c.real_sol_reserves,c.real_token_reserves,a.mayhem_base_token_vault.amount as u128,cap,retained);let native=a.quote_mint.key()==WSOL;",
     " let before_sol=if native{a.sol_vault.lamports()}else{a.mayhem_quote_token_vault.amount};let before_tokens=a.mayhem_base_token_vault.amount;",
     " let bump=[ctx.bumps.sol_vault];let seeds:&[&[u8]]=&[b\"sol-vault\",&bump];",
     " let cpi_result:Result<()> = if crate::pump_v2::buy_v2_recovered(CpiContext::new_with_signer(a.pump_program.key(),crate::pump_v2::BuyV2Accounts{"+accounts+"},&[seeds]),input,output,false).is_ok() { Ok(()) } else { Err(error!(BuyError::PumpCpiFailed)) };",
     " cpi_result?;",
     " a.mayhem_base_token_vault.reload()?;a.bonding_curve.reload()?;if !native{a.mayhem_quote_token_vault.reload()?;}",
     " let after_quote=if native{a.sol_vault.lamports()}else{a.mayhem_quote_token_vault.amount};",
    ]
    start = 376 - 21
    p = root/'src/instructions/pump_interface_v2.rs'; lines = p.read_text().split('\n')
    block = {start+n: t for n, t in enumerate(h)}
    block[393] = "    let sol=            before_sol-after_quote;"
    block[394] = "    let tokens=          a.mayhem_base_token_vault.amount-before_tokens;"
    block[395] = " crate::state::record_amm_buy(&mut a.global_params,&mut a.mayhem_state,sol,tokens,&a.quote_mint.key())?;"
    block[396] = event
    block[397] = " emit!(event);emit_cpi!(event);Ok(())"
    block[398] = "}"
    for ln, t in block.items():
        assert lines[ln-1] == '', (ln, lines[ln-1][:40])
        lines[ln-1] = t
    assert lines[375].count('error!(BuyError::PumpCpiFailed)') == 1
    assert lines[392].index('before_sol-after_quote') == 24 and lines[393].index('a.mayhem_base_token_vault.amount-before_tokens') == 25
    lines[2] = lines[2] + ' use super::buy_v2::BuyV2;'
    p.write_text('\n'.join(lines))
    lib = root/'src/lib.rs'; t = lib.read_text()
    assert t.count('instructions::buy_v2::handler(ctx,') == 1
    lib.write_text(t.replace('instructions::buy_v2::handler(ctx,', 'instructions::pump_interface_v2::buy_v2_handler(ctx,'))
