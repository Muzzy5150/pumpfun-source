from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path.cwd(); O=R/'work/parallel-main-user-quote-wrapper'; base=R/'work/parallel-main-integration/round30-source/programs/pump'; dst=O/'source01'
assert not dst.exists();shutil.copytree(base,dst)
module='''use anchor_lang::prelude::*;
use anchor_spl::token_interface::TokenInterface;

#[inline(never)]
pub fn transfer_native<'info>(
    destination: &AccountInfo<'info>,
    payer: &Signer<'info>,
    system_program: &Program<'info, System>,
    amount: u64,
) -> Result<()> {
    if amount == 0 { return Ok(()); }
    let accounts = anchor_lang::system_program::Transfer {
        to: destination.clone(),
        from: payer.to_account_info(),
    };
    anchor_lang::system_program::transfer(
        CpiContext::new(system_program.to_account_info(), accounts), amount,
    )
}

#[inline(never)]
pub fn transfer_from_user<'info>(
    native: bool,
    destination: &AccountInfo<'info>,
    payer: &Signer<'info>,
    system_program: &Program<'info, System>,
    amount: u64,
    token_program: &Interface<'info, TokenInterface>,
    quote_decimals: u8,
    quote_mint: &AccountInfo<'info>,
    quote_source: Option<&AccountInfo<'info>>,
    quote_destination: Option<&AccountInfo<'info>>,
) -> Result<()> {
    if native { return transfer_native(destination, payer, system_program, amount); }
    let from = quote_source.unwrap();
    let to = quote_destination.unwrap();
    let authority = payer.to_account_info();
    crate::sell_v2::quote_token_transfers::transfer_quote_tokens(
        token_program, from, to, authority, quote_decimals, quote_mint, amount, &[],
    )
}
'''
(dst/'src/user_quote_payments.rs').write_text(module)
p=dst/'src/trade_v3.rs';s=p.read_text();needle='''    if let Some(decimals)=quote_decimals {
      for (to,amount) in [(a.associated_quote_bonding_curve.to_account_info(),pool_quote),(a.buyback_fee_recipient.to_account_info(),total_buyback)] {
        if amount==0{continue}
        token_interface::transfer_checked(CpiContext::new(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_user.to_account_info(),mint:a.quote_mint.to_account_info(),to,authority:a.user.to_account_info()}),amount,decimals)?;
      }
    }else{
      anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to:a.bonding_curve.to_account_info()}),user_output)?;
'''
replacement='''    user_quote_payments::transfer_from_user(
        is_sol,a.bonding_curve.as_ref().as_ref(),&a.user,&a.system_program,
        if is_sol{user_output}else{pool_quote},&a.quote_token_program,
        quote_decimals.unwrap_or_default(),a.quote_mint.as_ref().as_ref(),
        if is_sol{None}else{Some(a.associated_quote_user.as_ref())},
        if is_sol{None}else{Some(a.associated_quote_bonding_curve.as_ref())},
    )?;
    if let Some(decimals)=quote_decimals {
      if total_buyback!=0 {
        token_interface::transfer_checked(CpiContext::new(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_user.to_account_info(),mint:a.quote_mint.to_account_info(),to:a.buyback_fee_recipient.to_account_info(),authority:a.user.to_account_info()}),total_buyback,decimals)?;
      }
    }else{
'''
assert s.count(needle)==2,s.count(needle);s=s.replace(needle,replacement)
s+='\n#[path="user_quote_payments.rs"]\npub mod user_quote_payments;\n';p.write_text(s)
p=dst/'src/buy_v2.rs';s=p.read_text();needle=''' if native{
  if quote>0{anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to:a.bonding_curve.to_account_info()}),quote)?;}
 }else if gross_quote>0{
  token_interface::transfer_checked(CpiContext::new(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_user.to_account_info(),mint:a.quote_mint.to_account_info(),to:a.associated_quote_bonding_curve.to_account_info(),authority:a.user.to_account_info()}),gross_quote,a.quote_mint.decimals)?;
 }
'''
replacement=''' crate::trade::user_quote_payments::transfer_from_user(
  native,a.bonding_curve.as_ref().as_ref(),&a.user,&a.system_program,
  if native{quote}else{gross_quote},&a.quote_token_program,a.quote_mint.decimals,
  a.quote_mint.as_ref().as_ref(),
  if native{None}else{Some(a.associated_quote_user.as_ref())},
  if native{None}else{Some(a.associated_quote_bonding_curve.as_ref())},
 )?;
'''
assert s.count(needle)==1;s=s.replace(needle,replacement);p.write_text(s)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.load(open(R/'work/parallel-main-window-boundary-audit/AUDIT.json'))
selected={0x97930,0x8df98}; rows=[c for c in a['calls'] if c['target'] in selected]
evidence={'status':'unbuilt isolated source hypothesis','original_sha256':sha(R/'evidence/original/pump/deployed.so'),'baseline':str(base.relative_to(R)),'changed':['src/trade_v3.rs','src/buy_v2.rs','src/user_quote_payments.rs'],'baseline_hashes':{f:sha(base/f) for f in ['src/trade_v3.rs','src/buy_v2.rs','Cargo.lock']},'source_hashes':{f:sha(dst/f) for f in ['src/trade_v3.rs','src/buy_v2.rs','src/user_quote_payments.rs','Cargo.lock']},'original_window':{'start':'0x97930','end':'0x97bf0','bytes':704},'direct_callers':rows,'abi':{'r1':'Result<()> output pointer','r2':'native bool','r3':'borrowed raw native destination AccountInfo','r4':'borrowed typed Signer','stack[-0x1000]':'borrowed Program<System>','stack[-0xff8]':'amount u64','stack[-0xff0]':'borrowed Interface<TokenInterface>','stack[-0xfe8]':'quote decimals u8','stack[-0xfe0]':'borrowed quote mint AccountInfo','stack[-0xfd8]':'Option<&AccountInfo> source','stack[-0xfd0]':'Option<&AccountInfo> destination'},'hypothesis':'A real shared quote-payment wrapper and its concrete native transfer boundary were inlined into current V2/V3 code. Recover them using actual three callsites. Source unwrap precedes destination; authority AccountInfo is owned; empty signer seeds.'}
(O/'HYPOTHESIS01.json').write_text(json.dumps(evidence,indent=2)+'\n')
for start,end,name in [(0x97930,0x97bf0,'original-wrapper.asm'),(0x8df98,0x8e450,'original-native.asm')]:
 out=subprocess.check_output(['/Users/shawwalters/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump','-d','--no-show-raw-insn',f'--start-address={start}',f'--stop-address={end}',str(R/'evidence/original/pump/deployed.so')],text=True);(O/name).write_text(out)
print(json.dumps({'source':str(dst),'hashes':evidence['source_hashes']},indent=2))
