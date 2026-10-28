from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path.cwd();P=R/'work/parallel-main-user-quote-generic';base=R/'work/parallel-main-user-quote-wrapper/source03';dst=P/'source01';assert not dst.exists();shutil.copytree(base,dst)
p=dst/'src/lib.rs';s=p.read_text();assert s.count("pub fn transfer_native<'info>(")==1 and s.count("pub fn transfer_from_user<'info>(")==1
s=s.replace("pub fn transfer_native<'info>(","pub fn transfer_native<'info, T: ToAccountInfo<'info>>(")
s=s.replace("pub fn transfer_from_user<'info>(","pub fn transfer_from_user<'info, T: ToAccountInfo<'info>>(")
s=s.replace("destination: &Account<'info, BondingCurve>,","destination: T,")
# Shared module needs no BondingCurve-specific import after generic reconstruction.
start=s.index('// Shared user-signed quote payment helpers.');prefix,helper=s[:start],s[start:];helper=helper.replace('    use crate::trade_types::BondingCurve;\n','');p.write_text(prefix+helper)
p=dst/'src/buy_v2.rs';s=p.read_text();old=''' if native{
  let to=if cashback_coin{a.user_volume_accumulator.to_account_info()}else{a.creator_vault.to_account_info()};
  if cf>0{anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to}),cf)?;}
 }else{
  let to=if cashback_coin{a.associated_user_volume_accumulator.to_account_info()}else{a.associated_creator_vault.to_account_info()};
  if cf>0{token_interface::transfer_checked(CpiContext::new(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_user.to_account_info(),mint:a.quote_mint.to_account_info(),to,authority:a.user.to_account_info()}),cf,a.quote_mint.decimals)?;}
 }
'''
new=''' let creator_destination=if cashback_coin{a.user_volume_accumulator.to_account_info()}else{a.creator_vault.to_account_info()};
 let creator_quote_destination=if native{None}else if cashback_coin{Some(a.associated_user_volume_accumulator.as_ref())}else{Some(a.associated_creator_vault.as_ref())};
 crate::user_quote_payments::transfer_from_user(
  native,a.system_program.as_ref(),&a.user,creator_destination,cf,&a.quote_token_program,
  a.quote_mint.decimals,a.quote_mint.as_ref().as_ref(),
  if native{None}else{Some(a.associated_quote_user.as_ref())},creator_quote_destination,
 )?;
'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();j={'status':'unbuilt generic ownership hypothesis','baseline':'work/parallel-main-user-quote-wrapper/source03','base_manifest_sha256':sha(R/'work/parallel-main-user-quote-wrapper/MANIFEST03.json'),'original_targets':{'0x97eb0':864,'0x8da98':1280},'evidence':'0x97eb0 shares both unwrap Location objects with0x97930 and0x97bf0; it owns destination AccountInfo and drops it on token branch, moves it to native callee on native branch. Four actual V2 creator/cashback callers.','changes':'Generic destination parameter retaining actual existing borrowed Account<BondingCurve> instantiation plus genuine owned AccountInfo creator/cashback instantiation. No dummy or retained calls.','source_hashes':{f:sha(dst/f)for f in ['src/lib.rs','src/buy_v2.rs','src/trade_v3.rs','Cargo.lock']}}
(P/'HYPOTHESIS01.json').write_text(json.dumps(j,indent=2)+'\n');
for start,end,name in [(0x97eb0,0x98210,'owned-wrapper-original.asm'),(0x8da98,0x8df98,'owned-native-original.asm')]:
 (P/name).write_text(subprocess.check_output(['/Users/shawwalters/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump','-d','--no-show-raw-insn',f'--start-address={start}',f'--stop-address={end}',str(R/'evidence/original/pump/deployed.so')],text=True))
print(json.dumps(j['source_hashes'],indent=2))
