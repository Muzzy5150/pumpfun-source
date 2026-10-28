import json, sys
D = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/mayhem-b'
F = 'src/instructions/sell_pump_swap.rs'
L = open(D + '/build/roots/work/programs/mayhem/' + F).read().split('\n')
ln = lambda n: L[n - 1]

def setlines(mods):
    if 66 in mods:
        old = '\n'.join(L[65:115]); nl = list(L[65:115])
        for n, t in mods.items(): nl[n - 66] = t
        return [F, old, '\n'.join(nl)]
    """mods: {lineno: newtext}; returns a single whole-region replacement over lines 67..115"""
    old = '\n'.join(L[66:115]); new_lines = list(L[66:115])
    for n, t in mods.items():
        new_lines[n - 67] = t
    return [F, old, '\n'.join(new_lines)]

NATIVE = {71: '', 72: '', 92: ' let native=a.quote_mint.key()==WSOL;', 93: ' let native_accounting=native||a.quote_mint.key()==Pubkey::default();'}
EQ = {79: ln(79).replace('.ok_or_else(math)?', '.ok_or(MayhemError::MathOverflow)?').replace('.map_err(|_|math())?', '.map_err(|_|MayhemError::MathOverflow)?')}
assert EQ[79] != ln(79)
HELPER = ('#[inline(always)] fn price_check(vt:u128,vs:u128,reference:u128,tolerance_bps:u16)->core::result::Result<(),MayhemError> {'
          ' if vt==0{return Err(MayhemError::MathOverflow);} let scaled=reference.checked_mul(tolerance_bps as u128);'
          ' let price=vs*1_000_000_000_000_000u128/vt; let delta=scaled.ok_or(MayhemError::MathOverflow)?/10_000;'
          ' let low=reference.checked_sub(delta).ok_or(MayhemError::MathOverflow)?; let high=reference.checked_add(delta).ok_or(MayhemError::MathOverflow)?;'
          ' if price<low||price>high{return Err(MayhemError::PumpCpiSlippage);} Ok(()) }')
PC = {67: HELPER, 85: ' price_check(a.pool_base_token_account.amount as u128,effective_quote as u128,reference,tolerance_bps)?;', 86: '', 87: '', 88: '', 89: '', 90: ''}
PCI = {85: ln(85), 86: ' if vt==0{return Err(MayhemError::MathOverflow.into());}', 87: ' let scaled=reference.checked_mul(tolerance_bps as u128);',
       88: ' let price=vs*1_000_000_000_000_000u128/vt;let delta=scaled.ok_or(MayhemError::MathOverflow)?/10_000;',
       89: ' let low=reference.checked_sub(delta).ok_or(MayhemError::MathOverflow)?;let high=reference.checked_add(delta).ok_or(MayhemError::MathOverflow)?;',
       90: ' if price<low||price>high{return Err(MayhemError::PumpCpiSlippage.into());}'}
def merge(*ds):
    r = {}
    for d in ds: r.update(d)
    return r
W = ['O0079']
specs = [{'label': 'm1-native-late', 'reps': [setlines(NATIVE)], 'windows': W},
         {'label': 'm2-native-eq', 'reps': [setlines(merge(NATIVE, EQ))], 'windows': W},
         {'label': 'm3-helper', 'reps': [setlines(merge(NATIVE, EQ, PC))], 'windows': W},
         {'label': 'm3b-inline', 'reps': [setlines(merge(NATIVE, EQ, PCI))], 'windows': W},
         {'label': 'm3c-helper-noeq', 'reps': [setlines(merge(NATIVE, PC))], 'windows': W}]
json.dump(specs, open(D + '/out/specs/m.json', 'w'), indent=1)
print(len(specs))

import re
BOXED = {'global_params','mayhem_state','mint','mayhem_token_vault','mayhem_quote_vault','pool','global_config','pool_base_token_account','pool_quote_token_account','protocol_fee_recipient_token_account','coin_creator_vault_ata'}
COPY_HELPER = ("fn info<'a,T:AsRef<AccountInfo<'a>>>(account:&T)->AccountInfo<'a> { let i=account.as_ref(); AccountInfo { key:i.key, lamports:std::rc::Rc::clone(&i.lamports), data:std::rc::Rc::clone(&i.data), owner:i.owner, _unused:i._unused, is_signer:i.is_signer, is_writable:i.is_writable, executable:i.executable } }")
def sub(line):
    return re.sub(r'a\.(\w+)\.to_account_info\(\)', lambda m: ('info(&*a.%s)' if m.group(1) in BOXED else 'info(&a.%s)') % m.group(1), line)
COPIES = {101: sub(ln(101)), 102: sub(ln(102))}
assert COPIES[101] != ln(101) and COPIES[102] != ln(102)
def with_helper(d):
    d = dict(d)
    if 67 in d:
        d[66] = ln(66) + ' ' + COPY_HELPER  # line 66 is the closing brace of the accounts struct
    else:
        d[67] = COPY_HELPER
    return d
specs = [{'label': 'm4-helper-copies', 'reps': [setlines(with_helper(merge(NATIVE, EQ, PC, COPIES)))], 'windows': W},
         {'label': 'm4b-eq-copies', 'reps': [setlines(with_helper(merge(NATIVE, EQ, COPIES)))], 'windows': W},
         {'label': 'm4c-native-copies', 'reps': [setlines(with_helper(merge(NATIVE, COPIES)))], 'windows': W},
         {'label': 'm4d-copies', 'reps': [setlines(with_helper(COPIES))], 'windows': W}]
json.dump(specs, open(D + '/out/specs/m4.json', 'w'), indent=1)
print('m4', len(specs))

COPY_HELPER_AI = '#[inline(always)] ' + COPY_HELPER
def with_helper_ai(d):
    d = dict(d)
    if 67 in d: d[66] = ln(66) + ' ' + COPY_HELPER_AI
    else: d[67] = COPY_HELPER_AI
    return d
specs = [{'label': 'm5-ai-copies', 'reps': [setlines(with_helper_ai(COPIES))], 'windows': W},
         {'label': 'm5-ai-native-copies', 'reps': [setlines(with_helper_ai(merge(NATIVE, COPIES)))], 'windows': W},
         {'label': 'm5-ai-helper-copies', 'reps': [setlines(with_helper_ai(merge(NATIVE, EQ, PC, COPIES)))], 'windows': W},
         {'label': 'm5-ai-eq-copies', 'reps': [setlines(with_helper_ai(merge(NATIVE, EQ, COPIES)))], 'windows': W}]
json.dump(specs, open(D + '/out/specs/m5.json', 'w'), indent=1)
print('m5', len(specs))

def helper(body):
    return ('#[inline(always)] fn price_check(vt:u128,vs:u128,reference:u128,tolerance_bps:u16)->core::result::Result<(),MayhemError> {' + body + ' Ok(()) }')
B_TAIL = (' let low=reference.checked_sub(delta).ok_or(MayhemError::MathOverflow)?; let high=reference.checked_add(delta).ok_or(MayhemError::MathOverflow)?;'
          ' if price<low||price>high{return Err(MayhemError::PumpCpiSlippage);}')
PC2 = dict(PC); PC2[67] = helper(' if vt==0{return Err(MayhemError::MathOverflow);} let price=vs*1_000_000_000_000_000u128/vt; let scaled=reference.checked_mul(tolerance_bps as u128); let delta=scaled.ok_or(MayhemError::MathOverflow)?/10_000;' + B_TAIL)
PC3 = dict(PC); PC3[67] = helper(' if vt==0{return Err(MayhemError::MathOverflow);} let price=vs*1_000_000_000_000_000u128/vt; let delta=reference.checked_mul(tolerance_bps as u128).ok_or(MayhemError::MathOverflow)?/10_000;' + B_TAIL)
PC4 = dict(PC); PC4[67] = helper(' if vt==0{return Err(MayhemError::MathOverflow);} let price=vs*1_000_000_000_000_000u128/vt; let scaled=reference.checked_mul(tolerance_bps as u128).ok_or(MayhemError::MathOverflow)?; let delta=scaled/10_000;' + B_TAIL)
specs = [{'label': 'm6-pc2', 'reps': [setlines(with_helper_ai(merge(NATIVE, EQ, PC2, COPIES)))], 'windows': W},
         {'label': 'm6-pc3', 'reps': [setlines(with_helper_ai(merge(NATIVE, EQ, PC3, COPIES)))], 'windows': W},
         {'label': 'm6-pc4', 'reps': [setlines(with_helper_ai(merge(NATIVE, EQ, PC4, COPIES)))], 'windows': W}]
json.dump(specs, open(D + '/out/specs/m6.json', 'w'), indent=1)
print('m6', len(specs))

EQ2 = {79: ' let effective_quote=(a.pool_quote_token_account.amount as i128).checked_add(a.pool.virtual_quote_reserves).and_then(|q|u64::try_from(q).ok()).ok_or(MayhemError::MathOverflow)?;'}
l101 = COPIES[101]; l102 = COPIES[102]
assert l101.startswith(' let accounts=crate::amm_cpi::cpi::accounts::Sell{') and l101.endswith('};')
struct = l101[len(' let accounts='):-1]
assert l102.startswith(' crate::amm_cpi::cpi::sell(CpiContext::new_with_signer(a.pump_swap_program.key(),accounts,&[seeds])')
rest102 = l102[len(' crate::amm_cpi::cpi::sell(CpiContext::new_with_signer(a.pump_swap_program.key(),accounts,&[seeds])'):]
INL = {101: ' crate::amm_cpi::cpi::sell(CpiContext::new_with_signer(a.pump_swap_program.key(),' + struct + ',&[seeds])',
       102: ' ' + rest102}
INLS = {101: ' crate::amm_cpi::cpi::sell(CpiContext::new_with_signer(a.pump_swap_program.key(),' + struct + ',&[&[b"sol-vault",&[ctx.bumps.sol_vault]]])',
        102: ' ' + rest102}
base6 = merge(NATIVE, EQ, PC2, COPIES)
specs = [{'label': 'm7a-eq2', 'reps': [setlines(with_helper_ai(merge(base6, EQ2)))], 'windows': W},
         {'label': 'm7b-eq2-inl', 'reps': [setlines(with_helper_ai(merge(base6, EQ2, INL)))], 'windows': W},
         {'label': 'm7c-eq2-inls', 'reps': [setlines(with_helper_ai(merge(base6, EQ2, INLS)))], 'windows': W},
         {'label': 'm7d-inl', 'reps': [setlines(with_helper_ai(merge(base6, INL)))], 'windows': W}]
json.dump(specs, open(D + '/out/specs/m7.json', 'w'), indent=1)
print('m7', len(specs))

best = merge(base6, EQ2, INLS)   # = m7c
def var79(lines79, extra=None, helper67=None):
    d = merge(best, {79: lines79})
    if extra: d = merge(d, extra)
    d = with_helper_ai(d)
    if helper67:
        d[66] = d[66] + ' ' + helper67
    return d
EQ3 = ' let effective_quote:u64=(a.pool_quote_token_account.amount as i128).checked_add(a.pool.virtual_quote_reserves).and_then(|q|q.try_into().ok()).ok_or(MayhemError::MathOverflow)?;'
EQ5 = ' let effective_quote=u64::try_from((a.pool_quote_token_account.amount as i128).checked_add(a.pool.virtual_quote_reserves).ok_or(MayhemError::MathOverflow)?).or(Err(MayhemError::MathOverflow))?;'
QH = "#[inline(always)] fn effective_quote(amount:u64,virtual_quote:i128)->core::result::Result<u64,MayhemError> { let q=(amount as i128).checked_add(virtual_quote).ok_or(MayhemError::MathOverflow)?; u64::try_from(q).map_err(|_|MayhemError::MathOverflow) }"
EQH = ' let effective_quote=effective_quote(a.pool_quote_token_account.amount,a.pool.virtual_quote_reserves)?;'
PCE = dict(PC2); PCE[67] = PC2[67].replace('->core::result::Result<(),MayhemError> {', '->Result<()> {').replace('return Err(MayhemError::MathOverflow);', 'return Err(MayhemError::MathOverflow.into());').replace('return Err(MayhemError::PumpCpiSlippage);', 'return Err(MayhemError::PumpCpiSlippage.into());')
specs = [{'label': 'm8a-eq3', 'reps': [setlines(var79(EQ3))], 'windows': W},
         {'label': 'm8b-eq5', 'reps': [setlines(var79(EQ5))], 'windows': W},
         {'label': 'm8c-qhelper', 'reps': [setlines(var79(EQH, helper67=QH))], 'windows': W},
         {'label': 'm8d-pc-anchor', 'reps': [setlines(var79(EQ2[79], extra={67: PCE[67]}))], 'windows': W}]
json.dump(specs, open(D + '/out/specs/m8.json', 'w'), indent=1)
print('m8', len(specs))
