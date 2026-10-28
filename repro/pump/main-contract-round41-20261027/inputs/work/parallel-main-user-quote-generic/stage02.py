from pathlib import Path
import hashlib,json,shutil
R=Path.cwd();P=R/'work/parallel-main-user-quote-generic';base=R/'work/parallel-main-user-quote-wrapper/source03';out=P/'source02';assert not out.exists();shutil.copytree(base,out)
p=out/'src/lib.rs';s=p.read_text();at=s.rfind('\n}');assert at>0
owned='''
    #[inline(never)]
    pub fn transfer_native_owned<'info>(
        system_program: &AccountInfo<'info>,
        payer: &Signer<'info>,
        destination: AccountInfo<'info>,
        amount: u64,
    ) -> Result<()> {
        anchor_lang::system_program::transfer(
            CpiContext::new(system_program.clone(), anchor_lang::system_program::Transfer {
                from: payer.to_account_info(),
                to: destination.clone(),
            }), amount,
        )
    }

    #[inline(never)]
    pub fn transfer_from_user_owned<'info>(
        native: bool,
        system_program: &AccountInfo<'info>,
        payer: &Signer<'info>,
        destination: AccountInfo<'info>,
        amount: u64,
        token_program: &Interface<'info, TokenInterface>,
        quote_decimals: u8,
        quote_mint: &AccountInfo<'info>,
        quote_source: Option<&AccountInfo<'info>>,
        quote_destination: Option<&AccountInfo<'info>>,
    ) -> Result<()> {
        if native { return transfer_native_owned(system_program, payer, destination, amount); }
        let from = quote_source.unwrap();
        let to = quote_destination.unwrap();
        let authority = payer.to_account_info();
        crate::sell_v2::quote_token_transfers::transfer_quote_tokens(
            token_program, from, to, authority, quote_decimals, quote_mint, amount, &[],
        )
    }
'''
s=s[:at]+owned+s[at:];p.write_text(s)
p=out/'src/buy_v2.rs';s=p.read_text();old=''' if native{
  let to=if cashback_coin{a.user_volume_accumulator.to_account_info()}else{a.creator_vault.to_account_info()};
  if cf>0{anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to}),cf)?;}
 }else{
  let to=if cashback_coin{a.associated_user_volume_accumulator.to_account_info()}else{a.associated_creator_vault.to_account_info()};
  if cf>0{token_interface::transfer_checked(CpiContext::new(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_user.to_account_info(),mint:a.quote_mint.to_account_info(),to,authority:a.user.to_account_info()}),cf,a.quote_mint.decimals)?;}
 }
'''
new=''' if cf>0 {
  let creator_destination=if cashback_coin{a.user_volume_accumulator.to_account_info()}else{a.creator_vault.to_account_info()};
  let creator_quote_destination=if native{None}else if cashback_coin{Some(a.associated_user_volume_accumulator.as_ref())}else{Some(a.associated_creator_vault.as_ref())};
  crate::user_quote_payments::transfer_from_user_owned(
   native,a.system_program.as_ref(),&a.user,creator_destination,cf,&a.quote_token_program,
   a.quote_mint.decimals,a.quote_mint.as_ref().as_ref(),
   if native{None}else{Some(a.associated_quote_user.as_ref())},creator_quote_destination,
  )?;
 }
'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();j={'status':'concrete owned API control following failed generic argument promotion','baseline':'immutable wrapper/source03; generic/source01 retained','source':'source02','evidence':'Original8da98 is unconditional, owned AccountInfo cloned into CPI then dropped. All original creator callers gate nonzero fees. Public concrete Signer preserves pointer level that generic trial promoted.','hypothesis':'Distinct concrete owned boundary represents actual wrapper/native ABI without altering recovered borrowed pair. Original source generic mechanism remains unproved.','hashes':{x:sha(out/x)for x in ['src/lib.rs','src/buy_v2.rs','src/trade_v3.rs']}}
(P/'HYPOTHESIS02.json').write_text(json.dumps(j,indent=2)+'\n');print(j['hashes'])
