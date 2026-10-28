from pathlib import Path
import shutil,hashlib,json
R=Path.cwd();P=R/'work/parallel-main-migration-payment-fix';base=R/'work/parallel-main-multihop-native-edge/source01';out=P/'source01';assert not out.exists();shutil.copytree(base,out)
module='''use anchor_lang::prelude::*;

#[inline(never)]
pub fn transfer_native<'info>(
    system_program: &AccountInfo<'info>, payer: &Signer<'info>,
    destination: &UncheckedAccount<'info>, amount: u64,
) -> Result<()> {
    if amount == 0 { return Ok(()); }
    anchor_lang::system_program::transfer(
        CpiContext::new(system_program.clone(), anchor_lang::system_program::Transfer {
            from: payer.to_account_info(), to: destination.to_account_info(),
        }), amount,
    )
}

#[derive(AnchorDeserialize)]
struct AmmConfigBase {
    admin: Pubkey,
    lp_fee_basis_points: u64,
    protocol_fee_basis_points: u64,
    disable_flags: u8,
    protocol_fee_recipients: [Pubkey; 8],
    coin_creator_fee_basis_points: u64,
    admin_set_coin_creator_authority: Pubkey,
    whitelist_pda: Pubkey,
    reserved_fee_recipient: Pubkey,
    mayhem_mode_enabled: bool,
    reserved_fee_recipients: [Pubkey; 7],
    is_cashback_enabled: bool,
    buyback_fee_recipients: [Pubkey; 8],
    buyback_basis_points: u64,
}

fn decode_boost_enabled(data: &[u8]) -> Option<bool> {
    if data.len() < 907 || data[..8] != [149, 8, 156, 202, 160, 252, 176, 217] { return None; }
    let mut body = &data[8..];
    let _base = AmmConfigBase::deserialize(&mut body).ok()?;
    if data.len() < 940 { return Some(false); }
    let _boost_authority = Pubkey::deserialize(&mut body).ok()?;
    let enabled = bool::deserialize(&mut body).ok()?;
    if data.len() >= 949 {
        let _creator_fee_configurable = bool::deserialize(&mut body).ok()?;
        let _max_configurable_creator_fee_bps = u64::deserialize(&mut body).ok()?;
    }
    Some(enabled)
}

pub(crate) fn boost_enabled(config: &AccountInfo) -> bool {
    config.try_borrow_data().ok().and_then(|data|decode_boost_enabled(&data)).unwrap_or(false)
}
'''
(out/'src/migration_native_payments.rs').write_text(module)
p=out/'src/migrate.rs';s=p.read_text();old=''' if !mayhem{require!(ctx.remaining_accounts.len()>=2,PumpError::NotEnoughRemainingAccounts);let boost=&ctx.remaining_accounts[0];let vault=&ctx.remaining_accounts[1];let top=rent.minimum_balance(165).saturating_sub(vault.lamports());if top>0{call(&sys,&[(&user,true,true),(&pa,false,true)],{let mut v=2u32.to_le_bytes().to_vec();v.extend_from_slice(&top.to_le_bytes());v},&[])?;}call(&am,&[(&pool,false,true),(&cfg,false,false),(&pa,true,true),(&mint,false,false),(&wsol,false,false),(&pb,false,true),(&pq,false,true),(boost,false,false),(vault,false,true),(&tok,false,false),(&sys,false,false),(&ata,false,false),(&ev,false,false),(&am,false,false)],vec![140,233,33,94,132,90,194,143],&[pas])?;}
'''
new=''' if !mayhem && (ctx.remaining_accounts.len()>=2 || native_payments::boost_enabled(&cfg)) {
  require!(ctx.remaining_accounts.len()>=2,PumpError::NotEnoughRemainingAccounts);
  let boost=&ctx.remaining_accounts[0];let vault=&ctx.remaining_accounts[1];
  let funding=Rent::get()?.minimum_balance(165);
  native_payments::transfer_native(a.system_program.as_ref(),&a.user,&a.pool_authority,funding)?;
  call(&am,&[(&pool,false,true),(&cfg,false,false),(&pa,true,true),(&mint,false,false),(&wsol,false,false),(&pb,false,true),(&pq,false,true),(boost,false,false),(vault,false,true),(&tok,false,false),(&sys,false,false),(&ata,false,false),(&ev,false,false),(&am,false,false)],vec![140,233,33,94,132,90,194,143],&[pas])?;
 }
'''
assert s.count(old)==1;s=s.replace(old,new);s+='\n#[path="migration_native_payments.rs"]\npub mod native_payments;\n';p.write_text(s)
p=out/'src/migrate_v2.rs';s=p.read_text();old=''' if native{move_lamports(&curve,&pa,fee)?;}else if fee>0{call(&sys,&[(&user,true,true),(&pa,false,true)],{let mut v=2u32.to_le_bytes().to_vec();v.extend_from_slice(&fee.to_le_bytes());v},&[])?;}
''';new=''' if native{move_lamports(&curve,&pa,fee)?;}else{crate::migrate::native_payments::transfer_native(a.system_program.as_ref(),&a.user,&a.pool_authority,fee)?;}
''';assert s.count(old)==1;s=s.replace(old,new)
old=''' if !mayhem{require!(ctx.remaining_accounts.len()>=2,PumpError::NotEnoughRemainingAccounts);let boost=&ctx.remaining_accounts[0];let vault=&ctx.remaining_accounts[1];let top=rent.minimum_balance(quote_account_size(&wsol)?).saturating_sub(vault.lamports());if top>0{call(&sys,&[(&user,true,true),(&pa,false,true)],{let mut v=2u32.to_le_bytes().to_vec();v.extend_from_slice(&top.to_le_bytes());v},&[])?;}call(&am,&[(&pool,false,true),(&cfg,false,false),(&pa,true,true),(&base_mint,false,false),(&wsol,false,false),(&pb,false,true),(&pq,false,true),(boost,false,false),(vault,false,true),(&qt,false,false),(&sys,false,false),(&ata,false,false),(&ev,false,false),(&am,false,false)],vec![140,233,33,94,132,90,194,143],&[pas])?;}
'''
new=''' if !mayhem && (ctx.remaining_accounts.len()>=2 || crate::migrate::native_payments::boost_enabled(&cfg)) {
  require!(ctx.remaining_accounts.len()>=2,PumpError::NotEnoughRemainingAccounts);
  let boost=&ctx.remaining_accounts[0];let vault=&ctx.remaining_accounts[1];
  let initial_balance=pa.lamports();let boost_rent=Rent::get()?;
  let funding=boost_rent.minimum_balance(quote_account_size(&wsol)?);
  crate::migrate::native_payments::transfer_native(a.system_program.as_ref(),&a.user,&a.pool_authority,funding)?;
  call(&am,&[(&pool,false,true),(&cfg,false,false),(&pa,true,true),(&base_mint,false,false),(&wsol,false,false),(&pb,false,true),(&pq,false,true),(boost,false,false),(vault,false,true),(&qt,false,false),(&sys,false,false),(&ata,false,false),(&ev,false,false),(&am,false,false)],vec![140,233,33,94,132,90,194,143],&[pas])?;
  let after_balance=pa.lamports();
  refund_pool_authority(a,ctx.bumps.pool_authority,&user,after_balance.saturating_sub(initial_balance))?;
  crate::migrate::native_payments::transfer_native(a.system_program.as_ref(),&a.user,&a.pool_authority,initial_balance.saturating_sub(after_balance))?;
 }
'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();changes={f:sha(out/f)for f in ['src/migrate.rs','src/migrate_v2.rs','src/migration_native_payments.rs']};(P/'STAGING01.json').write_text(json.dumps({'baseline':str(base.relative_to(R)),'source':str(out.relative_to(R)),'changes':changes,'proof_manifest_sha256':sha(R/'work/parallel-main-migration-payment-alias/READONLY-MANIFEST.json')},indent=2)+'\n');print(changes)
