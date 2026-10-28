from pathlib import Path
import shutil,json,hashlib
p=Path(__file__).parent;d=p/'source02';assert not d.exists();shutil.copytree(p/'source',d);f=d/'src/trade_v3.rs';s=f.read_text();a=s.index('pub fn sell(');b=s.index('pub fn buy(',a);q=s[a:b]
old='''    let (buyback_fee,retained)=v3_buyback_split(protocol_fee,buyback_bps);
    let buyback_received=if is_sol{buyback_fee}else{sub(buyback_fee,quote_transfer_fee(&a.quote_mint.to_account_info(),buyback_fee,false)?)?};
''';assert q.count(old)==1;q=q.replace(old,'');old='    let next_protocol=add(curve.protocol_fees,retained)?;\n';assert q.count(old)==1;q=q.replace(old,'')
x=q.index('    if let Some(decimals)=quote_decimals {');y=q.index('    let curve=&mut a.bonding_curve;',x)
new='''    let mint_key=a.base_mint.key();let bump=[ctx.bumps.bonding_curve];
    let seeds:&[&[u8]]=&[b"bonding-curve",mint_key.as_ref(),&bump];
    if let Some(decimals)=quote_decimals {
      if user_output!=0 {
        token_interface::transfer_checked(CpiContext::new_with_signer(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_bonding_curve.to_account_info(),mint:a.quote_mint.to_account_info(),to:a.associated_quote_user.to_account_info(),authority:a.bonding_curve.to_account_info()},&[seeds]),user_output,decimals)?;
      }
    }else{
      a.bonding_curve.sub_lamports(user_output)?;
      a.user.add_lamports(user_output)?;
    }
    let (buyback_fee,retained)=v3_buyback_split(protocol_fee,buyback_bps);
    let next_protocol=add(curve.protocol_fees,retained)?;
    let buyback_received=if is_sol{buyback_fee}else{sub(buyback_fee,crate::trade::quote_transfer_fee(&a.quote_mint.to_account_info(),buyback_fee,false)?)?};
    if let Some(decimals)=quote_decimals {
      if buyback_fee!=0 {
        token_interface::transfer_checked(CpiContext::new_with_signer(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_bonding_curve.to_account_info(),mint:a.quote_mint.to_account_info(),to:a.buyback_fee_recipient.to_account_info(),authority:a.bonding_curve.to_account_info()},&[seeds]),buyback_fee,decimals)?;
      }
    }else{
      a.bonding_curve.sub_lamports(buyback_fee)?;
      a.buyback_fee_recipient.add_lamports(buyback_fee)?;
    }
'''
q=q[:x]+new+q[y:];f.write_text(s[:a]+q+s[b:]);(p/'STAGING02.json').write_text(json.dumps({'base':'source, frozen initial compile-negative proposal','source':'source02','source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'corrections':['Qualified quote-fee function after scalar name shadowing.','Sell base/user payout precedes split as original invocation logs require.','Token protocol accrual overflow follows user transfer and precedes buyback transfer, as fresh protocol_max probe shows.'],'unchanged':'Buy/exact accounting afterpoolchecks andbeforelimits; panic texts andnumericorder.'},indent=2)+'\n')
