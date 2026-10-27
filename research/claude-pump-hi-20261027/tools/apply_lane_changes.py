#!/usr/bin/env python3
"""Apply the pump-hi lane's verified source changes to a main-Pump source tree.

Idempotent and content-addressed so it re-applies to later rounds:

1. #[program] handler order (window 0x11b758, the 8,696-byte dispatcher): permute the
   existing handler items into the order of the original dispatcher's discriminator
   comparisons (see reorder_program.py). Handler text is unchanged.
2. update_global_authority (window 0x1348c0, 3,264 bytes): the #[program] entry passes
   its Context by value to an ordinary handler fn that assigns the new authority first,
   then builds/emits the event. Behavior is unchanged (the event fields read the same
   keys; the authority store has no observable effect on them).
3. Legacy buy / buy_exact_sol_in wrappers (windows 0x12a4e0, 0x12abc8, 1,768 bytes each):
   the shared legacy buy handler takes its `exact` selector as a const generic, so each
   #[program] entry calls its own five-argument specialization, as the original wrappers
   do (the original has two handler bodies, 0x14c038 and 0x14f4e0). The handler body text
   and every source line stay where they were (`let exact=EXACT;` shares the signature line).
4. admin_set_idl_authority (window 0x19e3b0, 896 bytes = anchor_lang::system_program::
   transfer_with_seed): the original reclaims an uninitialized IDL account's lamports
   through Anchor's `system_program::transfer_with_seed` CPI helper (accounts from/base/to),
   not a hand-built instruction. The replaced block keeps its seven lines, so the
   handler's later `require!` coordinates do not move.
5. SetMayhemVirtualParams accounts layout (windows 0x1255a8 __global wrapper, 1,344 bytes,
   and 0xcf510 AccountsExit::exit, 576 bytes): the original accounts value is 1,728 bytes,
   with Global unboxed and the sol-vault authority held as an owned AccountInfo. Field
   offsets then equal the original's, e.g. global data at +1672 and the curve at +496.
   Owned sol_vault_authority fits the original try_accounts (0xcd3d8) better (0.49 vs 0.31)
   than the equal-size alternative of an owned token_program.
6. set_mayhem_virtual_params handler (window 0x137fc0, 2,912 bytes): `execute` is crate-private,
   so LLVM inlines it into the #[program] fn as in the original. That fn loads the event bump and
   accounts pointer at entry. The curve snapshot is read first, the sync helper takes Global and
   vault values as direct arguments, and the mint key is read with the event. The event is `Copy`
   and emitted without a clone. The file's line count is unchanged.

  apply_lane_changes.py --source-directory <crate dir containing src/lib.rs>
"""
import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

UGA_OLD = """    pub fn update_global_authority(ctx:Context<UpdateGlobalAuthority>)->Result<()>{
     let event=UpdateGlobalAuthorityEvent{global:ctx.accounts.global.key(),authority:ctx.accounts.authority.key(),new_authority:ctx.accounts.new_authority.key(),timestamp:Clock::get()?.unix_timestamp};
     ctx.accounts.global.authority=ctx.accounts.new_authority.key();emit!(event.clone());emit_cpi!(event);Ok(())
    }"""
UGA_NEW = """    pub fn update_global_authority(ctx:Context<UpdateGlobalAuthority>)->Result<()>{update_global_authority_handler(ctx)}"""
UGA_HANDLER = """fn update_global_authority_handler(ctx:Context<UpdateGlobalAuthority>)->Result<()>{
    ctx.accounts.global.authority=ctx.accounts.new_authority.key();
    let event=UpdateGlobalAuthorityEvent{global:ctx.accounts.global.key(),authority:ctx.accounts.authority.key(),new_authority:ctx.accounts.new_authority.key(),timestamp:Clock::get()?.unix_timestamp};
    emit!(event.clone());emit_cpi!(event);Ok(())
}
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-directory', type=Path, required=True)
    ap.add_argument('--without-handler-6', action='store_true',
                    help='skip change 6 (set_mayhem_virtual_params handler), reproducing the Round25 727 result')
    ap.add_argument('--with-fee-8', action='store_true',
                    help='also apply change 8 (fee_cpi linkage + generated-order metas for get_fees_with_quote_mint)')
    ap.add_argument('--with-cpi-7', action='store_true',
                    help='also apply change 7 (declare_program! generated CPI clients; see tools/cpi_changes.json)')
    a = ap.parse_args()
    lib = a.source_directory / 'src/lib.rs'
    subprocess.run([sys.executable, str(HERE / 'reorder_program.py'), '--lib', str(lib)], check=True)
    t = lib.read_text()
    if UGA_NEW in t and UGA_HANDLER in t:
        print('update_global_authority: already applied')
    else:
        assert t.count(UGA_OLD) == 1, 'update_global_authority source differs from the expected frontier text'
        t = t.replace(UGA_OLD, UGA_NEW)
        if not t.endswith('\n'):
            t += '\n'
        t += UGA_HANDLER
        lib.write_text(t)
        print('update_global_authority: applied')
    apply_buy_split(a.source_directory)
    apply_idl_transfer_with_seed(a.source_directory)
    apply_mayhem_params_layout(a.source_directory)
    if not a.without_handler_6:
        apply_mayhem_params_handler(a.source_directory)
    if a.with_cpi_7:
        apply_generated_cpi_clients(a.source_directory)
    if a.with_fee_8:
        apply_fee_client_order(a.source_directory)


FEE_SUBS = [('src/sell.rs', 'pub(crate) mod fee_cpi;\n', 'pub mod fee_cpi;\n'),
            ('src/fee_cpi.rs',
             '        anchor_lang::solana_program::instruction::Instruction {\n            program_id: ctx.program.key(),\n            accounts: ctx.to_account_metas(None),\n            data,\n        }\n',
             '        let accounts = ctx.to_account_metas(None);\n        anchor_lang::solana_program::instruction::Instruction {\n            program_id: ctx.program.key(),\n            accounts,\n            data,\n        }\n')]


def apply_fee_client_order(crate):
    """Change 8 (window 0x1176e0, pump_fees get_fees_with_quote_mint CPI client): give the
    client external linkage (pub mod fee_cpi; stops interprocedural constant propagation of
    is_pump_pool) and compute the account metas before the Instruction literal, the order
    of Anchor's generated CPI template."""
    fee = (crate / 'src/fee_cpi.rs').read_text()
    if 'crate::pump_fees::cpi::' in fee and FEE_SUBS[1][1] not in fee and FEE_SUBS[1][2] not in fee:
        # Round37+: the frontier calls the declare_program!(pump_fees) generated client itself
        print('fee client order: superseded by the frontier (generated pump_fees client)')
        return
    for rel, old, new in FEE_SUBS:
        p = crate / rel
        t = p.read_text()
        if new in t:
            continue
        assert t.count(old) == 1, f'{rel}: expected frontier text not found'
        p.write_text(t.replace(old, new))
    print('fee client order: applied')


def apply_generated_cpi_clients(crate):
    """Change 7: declare_program!(pump_amm)/(pump_fees) from the official upstream IDLs
    (evidence/upstream, pump-fun/pump-public-docs 639b87f; their instruction and account
    discriminators equal the original's) and call the generated cpi:: clients instead of
    hand-built instructions. Whole-line replacements keep every file's line count."""
    import json, shutil
    spec = json.loads((HERE / 'cpi_changes.json').read_text())
    root = next(p for p in HERE.parents if (p / 'evidence/original/pump/deployed.so').is_file())
    for dest, src in spec['idls'].items():
        d = crate / dest
        if d.exists():
            # Round37 ships idls/pump_fees.json, and composites may carry a derived pump_amm IDL
            # (e.g. GlobalConfig ending at boost_enabled): never overwrite an existing IDL.
            same = d.read_bytes() == (root / src).read_bytes()
            print(f'{dest}: kept the existing copy ({"equal to" if same else "differs from"} {src})')
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / src, d)
    lib = crate / 'src/lib.rs'
    t = lib.read_text()
    present = set(t.split('\n'))
    missing = [l for l in spec['lib_append'].split('\n') if l and l not in present]
    if missing:
        # Round37+ already declares pump_fees (lib.rs:65); append only what is not declared
        if not t.endswith('\n'):
            t += '\n'
        lib.write_text(t + '\n'.join(missing) + '\n')
    by_file = {}
    for c in spec['line_replacements']:
        by_file.setdefault(c['file'], []).append(c)
    for rel, cs in by_file.items():
        p = crate / rel
        lines = p.read_text().split('\n')
        for c in cs:
            if c['new'] in lines:
                continue
            assert lines.count(c['old']) == 1, f'{rel}: expected frontier line not found: {c["old"][:70]}'
            lines[lines.index(c['old'])] = c['new']
        p.write_text('\n'.join(lines))
    for c in spec.get('substring_replacements', []):
        p = crate / c['file']
        t = p.read_text()
        if c['new'] in t:
            continue
        assert t.count(c['old']) == 1, f'{c["file"]}: expected frontier expression not found: {c["old"][:70]}'
        p.write_text(t.replace(c['old'], c['new']))
    print('generated CPI clients: applied')


MVH_SUBS = [
    ("""pub fn execute(ctx: Context<SetMayhemVirtualParams>) -> Result<()> {
    let vault_amount = ctx.accounts.mayhem_token_vault.amount;
    let initial_real_token_reserves = ctx.accounts.global.initial_real_token_reserves;
    let mint = ctx.accounts.mint.key();
    let bc = &mut ctx.accounts.bonding_curve;
    let virtual_token_reserves = bc.virtual_token_reserves;
    let virtual_sol_reserves = bc.virtual_quote_reserves;

    let quote_mint = bc.quote_mint;
    bc.sync_virtual_quote_reserves(initial_real_token_reserves, vault_amount, &quote_mint)?;
""", """pub(crate) fn execute(ctx: Context<SetMayhemVirtualParams>) -> Result<()> {
    let bc = &mut ctx.accounts.bonding_curve;
    let virtual_token_reserves = bc.virtual_token_reserves;
    let virtual_sol_reserves = bc.virtual_quote_reserves;
    let quote_mint = bc.quote_mint;
    bc.sync_virtual_quote_reserves(
        ctx.accounts.global.initial_real_token_reserves,
        ctx.accounts.mayhem_token_vault.amount,
        &quote_mint,
    )?;
"""),
    ("        timestamp: Clock::get()?.unix_timestamp,\n        mint,\n",
     "        timestamp: Clock::get()?.unix_timestamp,\n        mint: ctx.accounts.mint.key(),\n"),
    ("    emit!(event.clone());\n    emit_cpi!(event);\n", "    emit!(event);\n    emit_cpi!(event);\n"),
    ("#[event]\n#[derive(Clone)]\npub struct UpdateMayhemVirtualParamsEvent {",
     "#[event]\n#[derive(Clone, Copy)]\npub struct UpdateMayhemVirtualParamsEvent {"),
]


def apply_mayhem_params_handler(crate):
    p = crate / 'src/mayhem_virtual_params.rs'
    t = p.read_text()
    if all(new in t for _, new in MVH_SUBS):
        print('set_mayhem_virtual_params handler: already applied')
        return
    for old, new in MVH_SUBS:
        assert t.count(old) == 1, 'set_mayhem_virtual_params source differs from the expected frontier text: ' + old[:60]
        assert old.count('\n') == new.count('\n')
        t = t.replace(old, new)
    p.write_text(t)
    print('set_mayhem_virtual_params handler: applied')


MVP_SUBS = [("    pub sol_vault_authority: UncheckedAccount<'info>,\n", "    pub sol_vault_authority: AccountInfo<'info>,\n"),
            ("    pub global: Box<Account<'info, Global>>,\n", "    pub global: Account<'info, Global>,\n")]


def apply_mayhem_params_layout(crate):
    p = crate / 'src/mayhem_virtual_params.rs'
    t = p.read_text()
    if all(new in t for _, new in MVP_SUBS):
        print('SetMayhemVirtualParams layout: already applied')
        return
    for old, new in MVP_SUBS:
        assert t.count(old) == 1, 'SetMayhemVirtualParams source differs from the expected frontier text: ' + old
        t = t.replace(old, new)
    p.write_text(t)
    print('SetMayhemVirtualParams layout: applied')


IDL_OLD = """        let signer=ctx.accounts.program_signer.key();
        let ix=anchor_lang::solana_program::system_instruction::transfer_with_seed(
            account.key,&signer,String::from("anchor:idl"),&crate::ID,
            &ctx.accounts.authority.key(),account.lamports());
        anchor_lang::solana_program::program::invoke_signed(&ix,&[
            account.clone(),ctx.accounts.program_signer.to_account_info(),ctx.accounts.authority.to_account_info(),ctx.accounts.system_program.to_account_info()
        ],&[&[&[ctx.bumps.program_signer]]])?;
"""
IDL_NEW = """        let cpi_accounts=anchor_lang::system_program::TransferWithSeed{
            from:account.clone(),base:ctx.accounts.program_signer.to_account_info(),
            to:ctx.accounts.authority.to_account_info()};
        let signer_seeds:&[&[&[u8]]]=&[&[&[ctx.bumps.program_signer]]];
        let cpi_context=CpiContext::new_with_signer(ctx.accounts.system_program.to_account_info(),cpi_accounts,signer_seeds);
        anchor_lang::system_program::transfer_with_seed(
            cpi_context,String::from("anchor:idl"),&crate::ID,account.lamports())?;
"""


def apply_idl_transfer_with_seed(crate):
    p = crate / 'src/admin_set_idl_authority.rs'
    if not p.exists():
        p = crate / 'src/idl_authority.rs'
    t = p.read_text()
    if IDL_NEW in t:
        print('admin_set_idl_authority transfer_with_seed: already applied')
        return
    if IDL_OLD not in t and 'anchor_lang::system_program::transfer_with_seed(' in t:
        print('admin_set_idl_authority transfer_with_seed: superseded by the frontier (already uses the Anchor helper)')
        return
    assert t.count(IDL_OLD) == 1, 'admin_set_idl_authority source differs from the expected frontier text'
    assert IDL_OLD.count('\n') == IDL_NEW.count('\n')
    p.write_text(t.replace(IDL_OLD, IDL_NEW))
    print('admin_set_idl_authority transfer_with_seed: applied')


BUY_SIG_OLD = "pub fn execute<'info>(ctx:Context<'_,'_,'_,'info,LegacyBuy<'info>>,input:u64,limit:u64,track:bool,partial:bool,exact:bool)->Result<()>{\n"
BUY_SIG_NEW = "pub fn execute<'info,const EXACT:bool>(ctx:Context<'_,'_,'_,'info,LegacyBuy<'info>>,input:u64,limit:u64,track:bool,partial:bool)->Result<()>{let exact=EXACT;\n"
BUY_CALLS = [("legacy_buy::execute(ctx,amount,max_sol_cost,track_volume.0,partial_fill.0,false)",
              "legacy_buy::execute::<false>(ctx,amount,max_sol_cost,track_volume.0,partial_fill.0)"),
             ("legacy_buy::execute(ctx,spendable_sol_in,min_tokens_out,track_volume.0,partial_fill.0,true)",
              "legacy_buy::execute::<true>(ctx,spendable_sol_in,min_tokens_out,track_volume.0,partial_fill.0)")]


def apply_buy_split(crate):
    lib = crate / 'src/lib.rs'
    buy = crate / 'src/buy.rs'
    if not buy.exists():
        buy = crate / 'src/legacy_buy.rs'
    b, t = buy.read_text(), lib.read_text()
    if BUY_SIG_NEW in b and all(new in t for _, new in BUY_CALLS):
        print('legacy buy const split: already applied')
        return
    assert b.count(BUY_SIG_OLD) == 1, 'legacy buy execute signature differs from the expected frontier text'
    assert all(t.count(old) == 1 for old, _ in BUY_CALLS), 'legacy buy #[program] calls differ from the expected frontier text'
    buy.write_text(b.replace(BUY_SIG_OLD, BUY_SIG_NEW))
    for old, new in BUY_CALLS:
        t = t.replace(old, new)
    lib.write_text(t)
    print('legacy buy const split: applied')


if __name__ == '__main__':
    main()
