#!/usr/bin/env python3
"""Lane mayhem-o79 variant generator for src/instructions/sell_pump_swap.rs (O0079 SellPumpSwap).

The accounts struct (lines 1-65) is kept byte-identical to parent-433.  Lines 66.. are
regenerated from named pieces so variants differ only where intended.  Every variant keeps
the handler inside lines 66-115 (blank-line padded) so other line numbers do not move.

usage: gen79.py SPECNAME 'label:key=val,key=val' ...   -> out/specs/SPECNAME.json
       gen79.py --show 'key=val,...'                     -> print the generated tail
"""
import json, sys
P433 = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/mayhem-env/parent-433/programs/mayhem/'
F = 'src/instructions/sell_pump_swap.rs'
L = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/mayhem-o79'
SRC = open(P433 + F).read()
HEAD, TAIL = SRC.split('\n}\n\nfn math()', 1)
HEAD += '\n}'
OLD_TAIL = '\nfn math()' + TAIL
assert SRC == HEAD + OLD_TAIL[0:0] + '\n' + OLD_TAIL[1:] or True

# ---------------------------------------------------------------- pieces
EQ = {
    # parent-433 form
    'parent': ' let effective_quote=u64::try_from((a.pool_quote_token_account.amount as i128).checked_add(a.pool.virtual_quote_reserves).ok_or_else(math)?).map_err(|_|math())?;',
    # mayhem-b m8c: inline(always) helper returning Result<u64,MayhemError>
    'helper': ' let effective_quote=effective_quote(a.pool_quote_token_account.amount,a.pool.virtual_quote_reserves)?;',
    # one ? over an and_then chain (m7a)
    'chain': ' let effective_quote=(a.pool_quote_token_account.amount as i128).checked_add(a.pool.virtual_quote_reserves).and_then(|q|u64::try_from(q).ok()).ok_or(MayhemError::MathOverflow)?;',
}
EQ_HELPERS = {
    'helper': "#[inline(always)] fn effective_quote(amount:u64,virtual_quote:i128)->core::result::Result<u64,MayhemError> { let q=(amount as i128).checked_add(virtual_quote).ok_or(MayhemError::MathOverflow)?; u64::try_from(q).map_err(|_|MayhemError::MathOverflow) }",
}
PRICE_CD = ' let price=(vs*1_000_000_000_000_000u128).checked_div(vt).ok_or(MayhemError::MathOverflow)?;'
SCALED = ' let scaled=reference.checked_mul(tolerance_bps as u128); let delta=scaled.ok_or(MayhemError::MathOverflow)?/10_000;'
CMP = ' if price<low||price>high{return Err(MayhemError::PumpCpiSlippage);}'
PC_BODY = {
    'pcC': PRICE_CD + SCALED + ' let (low,under)=reference.overflowing_sub(delta); let (high,over)=reference.overflowing_add(delta); if under||over{return Err(MayhemError::MathOverflow);}' + CMP,
    'pcD': PRICE_CD + SCALED + ' let low=reference.checked_sub(delta); let high=reference.checked_add(delta); let (Some(low),Some(high))=(low,high) else {return Err(MayhemError::MathOverflow)};' + CMP,
    'pcE': PRICE_CD + SCALED + ' match (reference.checked_sub(delta),reference.checked_add(delta)) {(Some(low),Some(high)) => if price<low||price>high{return Err(MayhemError::PumpCpiSlippage);}, _ => return Err(MayhemError::MathOverflow)}',
    'pcF': PRICE_CD + SCALED + ' if delta>reference{return Err(MayhemError::MathOverflow);} let high=reference.checked_add(delta).ok_or(MayhemError::MathOverflow)?; let low=reference-delta;' + CMP,
    'pcG': PRICE_CD + SCALED + ' let low=reference.checked_sub(delta).ok_or(MayhemError::MathOverflow)?; let high=reference.checked_add(delta).ok_or(MayhemError::MathOverflow)?; if !(low..=high).contains(&price){return Err(MayhemError::PumpCpiSlippage);}',
    'pcH': PRICE_CD + SCALED + ' let Some(low)=reference.checked_sub(delta) else {return Err(MayhemError::MathOverflow)}; let Some(high)=reference.checked_add(delta) else {return Err(MayhemError::MathOverflow)};' + CMP,
    # checked_div for the price (unlikely(vt==0) branch weights), price first
    'pc3': ' let price=(vs*1_000_000_000_000_000u128).checked_div(vt).ok_or(MayhemError::MathOverflow)?; let scaled=reference.checked_mul(tolerance_bps as u128); let delta=scaled.ok_or(MayhemError::MathOverflow)?/10_000; let low=reference.checked_sub(delta).ok_or(MayhemError::MathOverflow)?; let high=reference.checked_add(delta).ok_or(MayhemError::MathOverflow)?; if price<low||price>high{return Err(MayhemError::PumpCpiSlippage);}',
    # SellV2 order: scaled computed first, then checked_div price, then delta
    'pc4': ' let scaled=reference.checked_mul(tolerance_bps as u128); let price=(vs*1_000_000_000_000_000u128).checked_div(vt).ok_or(MayhemError::MathOverflow)?; let delta=scaled.ok_or(MayhemError::MathOverflow)?/10_000; let low=reference.checked_sub(delta).ok_or(MayhemError::MathOverflow)?; let high=reference.checked_add(delta).ok_or(MayhemError::MathOverflow)?; if price<low||price>high{return Err(MayhemError::PumpCpiSlippage);}',
    # checked_div + scaled checked inline with ?
    'pc5': ' let price=(vs*1_000_000_000_000_000u128).checked_div(vt).ok_or(MayhemError::MathOverflow)?; let delta=reference.checked_mul(tolerance_bps as u128).ok_or(MayhemError::MathOverflow)?/10_000; let low=reference.checked_sub(delta).ok_or(MayhemError::MathOverflow)?; let high=reference.checked_add(delta).ok_or(MayhemError::MathOverflow)?; if price<low||price>high{return Err(MayhemError::PumpCpiSlippage);}',
    # mayhem-b PC2 (price before checked_mul)
    'pc2': ' if vt==0{return Err(MayhemError::MathOverflow);} let price=vs*1_000_000_000_000_000u128/vt; let scaled=reference.checked_mul(tolerance_bps as u128); let delta=scaled.ok_or(MayhemError::MathOverflow)?/10_000; let low=reference.checked_sub(delta).ok_or(MayhemError::MathOverflow)?; let high=reference.checked_add(delta).ok_or(MayhemError::MathOverflow)?; if price<low||price>high{return Err(MayhemError::PumpCpiSlippage);}',
}
PC_CALL = ' price_check(a.pool_base_token_account.amount as u128,effective_quote as u128,reference,tolerance_bps)?;'

# Sell account fields in the ORIGINAL evaluation order (from the Rc-increment order in O0079)
ORIG_ORDER = ['user', 'pool', 'global_config', 'pool_base_token_account', 'pool_quote_token_account',
              'user_base_token_account', 'user_quote_token_account', 'quote_token_program', 'base_token_program',
              'system_program', 'quote_mint', 'base_mint', 'associated_token_program', 'event_authority', 'program',
              'protocol_fee_recipient', 'protocol_fee_recipient_token_account', 'coin_creator_vault_ata',
              'coin_creator_vault_authority', 'fee_config', 'fee_program']
IDL_ORDER = ['pool', 'user', 'global_config', 'base_mint', 'quote_mint', 'user_base_token_account',
             'user_quote_token_account', 'pool_base_token_account', 'pool_quote_token_account', 'protocol_fee_recipient',
             'protocol_fee_recipient_token_account', 'base_token_program', 'quote_token_program', 'system_program',
             'associated_token_program', 'event_authority', 'program', 'coin_creator_vault_ata',
             'coin_creator_vault_authority', 'fee_config', 'fee_program']
SRCACC = {'pool': 'pool', 'user': 'sol_vault', 'global_config': 'global_config', 'base_mint': 'mint',
          'quote_mint': 'quote_mint', 'user_base_token_account': 'mayhem_token_vault',
          'user_quote_token_account': 'mayhem_quote_vault', 'pool_base_token_account': 'pool_base_token_account',
          'pool_quote_token_account': 'pool_quote_token_account', 'protocol_fee_recipient': 'protocol_fee_recipient',
          'protocol_fee_recipient_token_account': 'protocol_fee_recipient_token_account',
          'base_token_program': 'base_token_program', 'quote_token_program': 'quote_token_program',
          'system_program': 'system_program', 'associated_token_program': 'associated_token_program',
          'event_authority': 'pump_swap_event_authority', 'program': 'pump_swap_program',
          'coin_creator_vault_ata': 'coin_creator_vault_ata', 'coin_creator_vault_authority': 'coin_creator_vault_authority',
          'fee_config': 'fee_config', 'fee_program': 'fee_program'}
assert sorted(ORIG_ORDER) == sorted(IDL_ORDER) == sorted(SRCACC)


def sell_struct(order):
    return 'crate::amm_cpi::cpi::accounts::Sell{' + ','.join(f'{f}:a.{SRCACC[f]}.to_account_info()' for f in order) + '}'


SEEDS = {
    'inline': '&[&[b"sol-vault",&[ctx.bumps.sol_vault]]]',
    'var': '&[seeds]',
}

# SellEvent literal pieces (keys are short names; EV builds literals in a chosen order)
EVF = {
    'side': 'side:1', 'sv': 'sol_vault:a.sol_vault.key()', 'mint': 'mint:a.mint.key()',
    'sa': 'sol_amount:if native{sol}else{0}', 'ta': 'token_amount:tokens',
    'svb': 'sol_vault_balance:if native{a.sol_vault.lamports()}else{0}',
    'svbq': 'sol_vault_balance:if native{quote_vault_balance}else{0}',
    'tvb': 'token_vault_balance:a.mayhem_token_vault.amount',
    'ssd': 'state_sol_deployed:if native{a.mayhem_state.field_56}else{0}', 'stn': 'state_token_net:a.mayhem_state.field_72',
    'vs': 'virtual_sol:if native{a.pool_quote_token_account.amount}else{0}', 'vt': 'virtual_tokens:a.pool_base_token_account.amount',
    'gsd': 'global_sol_deployed:if native{a.global_params.sol_deployed}else{0}', 'ts': 'timestamp:Clock::get()?.unix_timestamp',
    'et': 'end_timestamp:a.mayhem_state.end_timestamp', 'rs': 'real_sol:if native{a.pool_quote_token_account.amount}else{0}',
    'rt': 'real_tokens:a.pool_base_token_account.amount', 'ver': 'version:a.global_params.version', 'rrb': 'retained_reserve_bps',
    'qa': 'quote_amount:sol', 'qvb': 'quote_vault_balance:after_quote', 'qvbl': 'quote_vault_balance',
    'qvbi': 'quote_vault_balance:if native{a.sol_vault.lamports()}else{a.mayhem_quote_vault.amount}',
    'sqd': 'state_quote_deployed:a.mayhem_state.field_56', 'vq': 'virtual_quote:a.pool_quote_token_account.amount',
    'gqd': 'global_quote_deployed:if native_accounting{a.global_params.sol_deployed}else{a.global_params.stable_deployed}',
    'gqdn': 'global_quote_deployed:if native{a.global_params.sol_deployed}else{a.global_params.stable_deployed}',
    'rq': 'real_quote:a.pool_quote_token_account.amount', 'qm': 'quote_mint:if native{Pubkey::default()}else{a.quote_mint.key()}',
}
PARENT_EV = ['side', 'sv', 'mint', 'sa', 'ta', 'svb', 'tvb', 'ssd', 'stn', 'vs', 'vt', 'gsd', 'ts', 'et', 'rs', 'rt', 'ver', 'rrb',
             'qa', 'qvb', 'sqd', 'vq', 'gqd', 'rq', 'qm']
QVB_LOCAL = ' let quote_vault_balance=if native{a.sol_vault.lamports()}else{a.mayhem_quote_vault.amount};'


def ev(order, pre=''):
    return pre + ' let event=SellEvent{' + ','.join(EVF[k] for k in order) + '};'


EV = {
    'p': ev(PARENT_EV),
    'p2': ev([{'gqd': 'gqdn', 'qvb': 'qvbi'}.get(k, k) for k in PARENT_EV]),
    'p3': ev([{'gqd': 'gqdn', 'qvb': 'qvbl', 'svb': 'svbq'}.get(k, k) for k in PARENT_EV], QVB_LOCAL),
    'n1': ev(['side', 'sa', 'svbq', 'ssd', 'vs', 'gsd', 'rs', 'qvbl', 'sqd', 'vq', 'gqdn', 'rq', 'qm', 'sv', 'mint', 'ta', 'tvb',
              'stn', 'vt', 'et', 'ts', 'rt', 'ver', 'rrb', 'qa'], QVB_LOCAL),
    'n2': ev(['side', 'sa', 'svbq', 'ssd', 'vs', 'gsd', 'rs', 'qvbl', 'sqd', 'vq', 'gqdn', 'rq', 'qm', 'sv', 'mint', 'ta', 'tvb',
              'stn', 'vt', 'ts', 'et', 'rt', 'ver', 'rrb', 'qa'], QVB_LOCAL),
}


def build(o):
    o = dict(o)
    eq = o.get('eq', 'helper'); pc = o.get('pc', 'pc2'); order = ORIG_ORDER if o.get('order', 'orig') == 'orig' else IDL_ORDER
    s1 = o.get('s1', 'inline'); s2 = o.get('s2', 'inline')
    pre = []   # helper fns placed after the struct (line 66 onwards on one line each)
    if eq in EQ_HELPERS:
        pre.append(EQ_HELPERS[eq])
    pre.append('#[inline(always)] fn price_check(vt:u128,vs:u128,reference:u128,tolerance_bps:u16)->core::result::Result<(),MayhemError> {' + PC_BODY[pc] + ' Ok(()) }')
    pre.append('fn math()->Error {MayhemError::MathOverflow.into()}')
    body = []
    body.append('pub fn handler(ctx:Context<SellPumpSwap>,reference:u128,tolerance_bps:u16,retained_reserve_bps:u16)->Result<()> {')
    body.append(' let a=&mut *ctx.accounts;')
    body.append(' a.mayhem_state.validate_trade(&a.global_params)?;')
    body.append(o.get('eqline', EQ[eq]))
    body.append(' a.mayhem_state.validate_quote(effective_quote,&a.global_params,&a.quote_mint.key())?;')
    body.append(o.get('pcline', PC_CALL))
    body.append(' let (input,minimum)=crate::state::sell_quote(&a.global_params,a.pool_base_token_account.amount,effective_quote,a.mayhem_token_vault.amount,retained_reserve_bps,a.quote_mint.key())?;')
    body.append(o.get('native', ' let native=a.quote_mint.key()==WSOL;'))
    body.append(' let native_accounting=native||a.quote_mint.key()==Pubkey::default();')
    body.append(o.get('before', ' let before_sol=if native{a.sol_vault.lamports()}else{a.mayhem_quote_vault.amount};let before_tokens=a.mayhem_token_vault.amount;'))
    if s1 == 'var' or s2 == 'var':
        body.append(' let bump=[ctx.bumps.sol_vault];let seeds:&[&[u8]]=&[b"sol-vault",&bump];')
    if 'cpi' in o:
        body.append(o['cpi'])
    else:
        body.append(' crate::amm_cpi::cpi::sell(CpiContext::new_with_signer(a.pump_swap_program.key(),' + sell_struct(order) + ',' + SEEDS[s1] + ')')
        body.append(' .with_remaining_accounts(vec![a.buyback_recipient.to_account_info(),a.buyback_recipient_ata.to_account_info()]),input,minimum).map_err(super::pump_amm_interface::sell_cpi_failed)?;')
    body.append(o.get('close', ' if native {curve_accounts::token_interface::close_account(CpiContext::new_with_signer(a.quote_token_program.key(),curve_accounts::token_interface::CloseAccount{account:a.mayhem_quote_vault.to_account_info(),destination:a.sol_vault.to_account_info(),authority:a.sol_vault.to_account_info()},' + SEEDS[s2] + '))?;}'))
    body.append(' a.mayhem_token_vault.reload()?;a.pool_base_token_account.reload()?;a.pool_quote_token_account.reload()?;if !native{a.mayhem_quote_vault.reload()?;}')
    body.append(' let after_quote=if native{a.sol_vault.lamports()}else{a.mayhem_quote_vault.amount};')
    body.append(' let (sol,tokens)=super::pump_amm_interface::sold_amounts(before_sol,after_quote,before_tokens,a.mayhem_token_vault.amount);')
    body.append(' crate::state::record_sell(&mut a.global_params,&mut a.mayhem_state,sol,tokens,&a.quote_mint.key())?;')
    body.append(EV[o.get('ev', 'p')] if o.get('ev', 'p') in EV else o['ev'])
    body.append(' emit!(event);emit_cpi!(event);Ok(())')
    if o.get('nonacc'):
        body = [l for l in body if 'let native_accounting' not in l]
    for k, v in o.items():
        if k.startswith('sub:'):
            old, new = k[4:], v
            assert sum(l.count(old) for l in body + pre) == 1, (old, sum(l.count(old) for l in body + pre))
            body = [l.replace(old, new) for l in body]; pre = [l.replace(old, new) for l in pre]
    # lay out: pre helpers on lines 66.., handler starts at 69 (parent) or later; pad so '}' lands on line 115
    lines = HEAD.split('\n')  # lines 1..66, last is the struct's closing brace
    assert len(lines) == 66, len(lines)
    assert len(pre) >= 2
    if len(pre) > 2:
        lines[-1] = '} ' + ' '.join(pre[:-2])
    out = lines + [pre[-2], pre[-1]]   # lines 67, 68; handler starts at 69
    out += body
    pad = 115 - len(out) - 1
    assert pad >= 0, ('too many lines', len(out))
    out += [''] * pad + ['}', '']
    return '\n'.join(out)


def spec(label, o):
    new = build(o)
    return {'label': label, 'reps': [[F, SRC, new]], 'windows': ['O0079']}


def parse(arg):
    label, _, kv = arg.partition(':')
    o = {}
    for part in filter(None, kv.split(',')):
        k, _, v = part.partition('=')
        o[k] = v
    return label, o


if __name__ == '__main__':
    if sys.argv[1] == '--show':
        print(build(parse('x:' + (sys.argv[2] if len(sys.argv) > 2 else ''))[1])[len(HEAD):])
        sys.exit()
    name = sys.argv[1]
    specs = [spec(*parse(a)) for a in sys.argv[2:]]
    json.dump(specs, open(f'{L}/out/specs/{name}.json', 'w'), indent=1)
    print(name, [s['label'] for s in specs])
