from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path.cwd();P=R/'work/parallel-main-user-quote-recipient';base=R/'work/parallel-main-user-quote-generic/source02';out=P/'source01';assert not out.exists();shutil.copytree(base,out)
p=out/'src/lib.rs';s=p.read_text();at=s.rfind('\n}');assert at>0
addition='''
    #[inline(never)]
    pub fn transfer_native_recipient<'info>(
        system_program: &AccountInfo<'info>,
        payer: &Signer<'info>,
        destination: &&UncheckedAccount<'info>,
        amount: u64,
    ) -> Result<()> {
        if amount == 0 { return Ok(()); }
        anchor_lang::system_program::transfer(
            CpiContext::new(system_program.clone(), anchor_lang::system_program::Transfer {
                from: payer.to_account_info(),
                to: destination.to_account_info(),
            }), amount,
        )
    }

    #[inline(never)]
    pub fn transfer_from_user_recipient<'info>(
        native: bool,
        system_program: &AccountInfo<'info>,
        payer: &Signer<'info>,
        destination: &&UncheckedAccount<'info>,
        amount: u64,
        token_program: &Interface<'info, TokenInterface>,
        quote_decimals: u8,
        quote_mint: &AccountInfo<'info>,
        quote_source: Option<&AccountInfo<'info>>,
        quote_destination: Option<&AccountInfo<'info>>,
    ) -> Result<()> {
        if native { return transfer_native_recipient(system_program, payer, destination, amount); }
        let from = quote_source.unwrap();
        let to = quote_destination.unwrap();
        let authority = payer.to_account_info();
        crate::sell_v2::quote_token_transfers::transfer_quote_tokens(
            token_program, from, to, authority, quote_decimals, quote_mint, amount, &[],
        )
    }
'''
p.write_text(s[:at]+addition+s[at:])
p=out/'src/buy_v2.rs';s=p.read_text();old=''' if native{
  recipient_payments::transfer_native(a.system_program.as_ref(),&a.fee_recipient,a.user.as_ref(),protocol_fee)?;
  recipient_payments::transfer_native(a.system_program.as_ref(),bb,a.user.as_ref(),bf)?;
 }else{
  if protocol_fee>0{token_interface::transfer_checked(CpiContext::new(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_user.to_account_info(),mint:a.quote_mint.to_account_info(),to:a.associated_quote_fee_recipient.to_account_info(),authority:a.user.to_account_info()}),protocol_fee,a.quote_mint.decimals)?;}
  if bf>0{token_interface::transfer_checked(CpiContext::new(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_user.to_account_info(),mint:a.quote_mint.to_account_info(),to:a.associated_quote_buyback_fee_recipient.to_account_info(),authority:a.user.to_account_info()}),bf,a.quote_mint.decimals)?;}
 }
'''
new=''' for (recipient,quote_recipient,amount) in [(&a.fee_recipient,&a.associated_quote_fee_recipient,protocol_fee),(bb,&a.associated_quote_buyback_fee_recipient,bf)].iter() {
  crate::user_quote_payments::transfer_from_user_recipient(
   native,a.system_program.as_ref(),&a.user,recipient,*amount,&a.quote_token_program,
   a.quote_mint.decimals,a.quote_mint.as_ref().as_ref(),
   if native{None}else{Some(a.associated_quote_user.as_ref())},
   if native{None}else{Some(quote_recipient.as_ref())},
  )?;
 }
'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();j={'status':'unbuilt concrete recipient ABI control','baseline':'work/parallel-main-user-quote-generic/source02','baseline_manifest_sha256':sha(R/'work/parallel-main-user-quote-generic/MANIFEST.json'),'targets':{'0x97bf0':704,'0x8d108':1216},'evidence':'Native8d108 performs two pointer loads from destination at8d2d8 and8d2e0, matching a nested borrowed UncheckedAccount. Original wrapper passes a stack slot holding recipient ref. System then payer then recipient clone order. Four original V2 fee/buyback sites.','changes':'Two real recipient payments iterate refs in original order; dedicated concrete wrapper/native pair with nested borrowed recipient. Existing borrowed/owned pairs untouched. No fee math or legacy edits.','source_hashes':{f:sha(out/f)for f in ['src/lib.rs','src/buy_v2.rs','src/trade_v3.rs']}}
(P/'HYPOTHESIS01.json').write_text(json.dumps(j,indent=2)+'\n')
for start,end,name in [(0x97bf0,0x97eb0,'original-wrapper.asm'),(0x8d108,0x8d5c8,'original-native.asm'),(0x13d8a0,0x13db10,'original-v2-callers.asm')]:
 (P/name).write_text(subprocess.check_output(['/Users/shawwalters/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump','-d','--no-show-raw-insn',f'--start-address={start}',f'--stop-address={end}',str(R/'evidence/original/pump/deployed.so')],text=True))
print(json.dumps(j['source_hashes'],indent=2))
