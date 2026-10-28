from pathlib import Path
import shutil,hashlib,json
P=Path(__file__).resolve().parent;R=P.parents[1];base=R/'work/parallel-main-v3-buyback-assert/source02';dest=P/'source01';shutil.copytree(base,dest);f=dest/'src/trade_v3.rs';s=f.read_text()
# Refactor the existing byte-validating scan into a selected-fee snapshot.
start=s.index('pub(crate) fn quote_transfer_fee(');end=s.index('\n#[event]',start)
old=s[start:end]
snapshot=old.replace('pub(crate) fn quote_transfer_fee(mint:&AccountInfo,amount:u64,inverse:bool)->Result<u64>{','fn quote_fee_snapshot(mint:&AccountInfo)->Result<Option<(u64,u64,u64)>>{').replace('if mint.owner==&anchor_spl::token::ID{return Ok(0);}','if mint.owner==&anchor_spl::token::ID{return Ok(None);}')
a=snapshot.index('    match selected {')
snapshot=snapshot[:a]+'''    Ok(match selected {
        Some(fees)=>{
            let epoch=Clock::get()?.epoch;
            let selected=fees.get_epoch_fee(epoch);
            Some((u64::from(selected.epoch),u64::from(selected.maximum_fee),u16::from(selected.transfer_fee_basis_points) as u64))
        }
        None=>None,
    })
}

pub(crate) fn quote_transfer_fee(mint:&AccountInfo,amount:u64,inverse:bool)->Result<u64>{
    let snapshot=quote_fee_snapshot(mint)?;
    match snapshot {
        Some((epoch,maximum_fee,basis_points))=>{
            let selected=anchor_spl::token_2022::spl_token_2022::extension::transfer_fee::TransferFee{
                epoch:epoch.into(),maximum_fee:maximum_fee.into(),transfer_fee_basis_points:(basis_points as u16).into(),
            };
            let fee=if inverse{selected.calculate_inverse_fee(amount)}else{selected.calculate_fee(amount)};
            fee.ok_or_else(||error!(PumpError::Overflow))
        }
        None=>Ok(0),
    }
}

#[inline(never)]
pub fn quote_pre_fee_amount(snapshot:&Option<(u64,u64,u64)>,amount:u64)->Result<u64>{
    match snapshot {
        Some((epoch,maximum_fee,basis_points))=>{
            let selected=anchor_spl::token_2022::spl_token_2022::extension::transfer_fee::TransferFee{
                epoch:(*epoch).into(),maximum_fee:(*maximum_fee).into(),transfer_fee_basis_points:(*basis_points as u16).into(),
            };
            selected.calculate_pre_fee_amount(amount).ok_or_else(||error!(PumpError::Overflow))
        }
        None=>Ok(amount),
    }
}

#[inline(never)]
pub fn quote_with_fees(quote:u64,protocol:u64,creator:u64)->Result<u64>{
    quote.checked_add(protocol).and_then(|amount|amount.checked_add(creator))
        .ok_or_else(||error!(PumpError::Overflow))
}

/// Return the pool transfer, total buyback transfer, and pool transfer fee.
#[inline(never)]
pub fn buy_quote_amounts(
    buyback_basis_points:u64, is_mayhem:bool, quote_fee:&Option<(u64,u64,u64)>,
    quote:u64, protocol_fee:u64, creator_fee:u64,
    post:Option<&(u64,u64,u64,u64,u64,u64,u64,u64)>,
)->Result<(u64,u64,u64)>{
    let buyback=if is_mayhem {0}else{
        let amount=u64::try_from(protocol_fee as u128*buyback_basis_points as u128/10000)
            .expect("buyback fee is at most protocol_fee");
        protocol_fee.checked_sub(amount).expect("buyback_fee never exceeds protocol_fee");
        amount
    };
    let post_buyback=if is_mayhem {0}else if let Some(post)=post{
        let amount=u64::try_from(post.0 as u128*buyback_basis_points as u128/10000)
            .expect("buyback fee is at most protocol_fee");
        post.0.checked_sub(amount).expect("buyback_fee never exceeds protocol_fee");
        amount
    }else{0};
    let total_buyback=buyback.checked_add(post_buyback).ok_or_else(||error!(PumpError::Overflow))?;
    let initial_cost=quote_with_fees(quote,protocol_fee,creator_fee)?;
    let total_cost=if let Some(post)=post{
        let post_cost=quote_with_fees(post.5,post.0,post.1)?;
        initial_cost.checked_add(post_cost).ok_or_else(||error!(PumpError::Overflow))?
    }else{initial_cost};
    let net_pool_quote=total_cost.checked_sub(total_buyback).ok_or_else(||error!(PumpError::Overflow))?;
    let pool_quote=quote_pre_fee_amount(quote_fee,net_pool_quote)?;
    require_gte!(pool_quote,net_pool_quote,PumpError::Overflow);
    Ok((pool_quote,total_buyback,pool_quote-net_pool_quote))
}
'''
s=s[:start]+snapshot+s[end:]
# Limit changes to both buy bodies; sell retains its accepted ordering.
start=s.index('pub fn buy(');head=s[:start];buys=s[start:]
needle='    let is_sol=quote_decimals.is_none();'
assert buys.count(needle)==2
buys=buys.replace(needle,needle+'\n    let quote_fee=if is_sol{None}else{quote_fee_snapshot(&a.quote_mint.to_account_info())?};')
needle='    let (buyback_fee,retained)=v3_buyback_split(protocol_fee,buyback_bps);\n    let (post_buyback,post_retained)=v3_buyback_split(post_protocol,buyback_bps);'
assert buys.count(needle)==2
new='''    let post=if POST_ACTIVE{Some((post_protocol,post_creator,fees.protocol_fee_bps,creator_bps,post_base,post_quote,pool_base_before,pool_quote_before))}else{None};
    let (pool_quote,total_buyback,quote_transfer_fee)=buy_quote_amounts(a.global.buyback_basis_points,curve.is_mayhem_mode,&quote_fee,quote,protocol_fee,creator_fee,post.as_ref())?;
    let (buyback_fee,retained)=v3_buyback_split(protocol_fee,buyback_bps);
    let (post_buyback,post_retained)=v3_buyback_split(post_protocol,buyback_bps);'''
buys=buys.replace(needle,new.replace('POST_ACTIVE','crossing'),1).replace(needle,new.replace('POST_ACTIVE','post_active'),1)
old='''    let total_buyback=add(buyback_fee,post_buyback)?;
    let user_output=add(first_cost,add(add(post_quote,post_protocol)?,post_creator)?)?;
    let net_pool_quote=sub(user_output,total_buyback)?;
    let buyback_received=if is_sol{buyback_fee}else{sub(buyback_fee,quote_transfer_fee(&a.quote_mint.to_account_info(),buyback_fee,false)?)?};
    let quote_transfer_fee=if is_sol{0}else{quote_transfer_fee(&a.quote_mint.to_account_info(),net_pool_quote,true)?};
    let pool_quote=add(net_pool_quote,quote_transfer_fee)?;'''
new='''    let user_output=add(sub(pool_quote,quote_transfer_fee)?,total_buyback)?;
    let buyback_received=if is_sol{buyback_fee}else{sub(buyback_fee,crate::trade::quote_transfer_fee(&a.quote_mint.to_account_info(),buyback_fee,false)?)?};'''
assert old in buys;buys=buys.replace(old,new,1)
buys=buys.replace('    let user_output=add(first_cost,add(add(post_quote,post_protocol)?,post_creator)?)?;','    let user_output=add(sub(pool_quote,quote_transfer_fee)?,total_buyback)?;',1)
old='''    let total_buyback=add(buyback_fee,post_buyback)?;
    let net_pool_quote=sub(user_output,total_buyback)?;
    // Main-event buyback_fee reports the net of the first-fill buyback only; any
    // post-complete buyback is carried separately by PostCompleteBuyEvent.
    let buyback_received=if is_sol{buyback_fee}else{sub(buyback_fee,quote_transfer_fee(&a.quote_mint.to_account_info(),buyback_fee,false)?)?};
    let quote_transfer_fee=if is_sol{0}else{quote_transfer_fee(&a.quote_mint.to_account_info(),net_pool_quote,true)?};
    let pool_quote=add(net_pool_quote,quote_transfer_fee)?;'''
new='''    // Main-event buyback_fee reports the net of the first-fill buyback only; any
    // post-complete buyback is carried separately by PostCompleteBuyEvent.
    let buyback_received=if is_sol{buyback_fee}else{sub(buyback_fee,crate::trade::quote_transfer_fee(&a.quote_mint.to_account_info(),buyback_fee,false)?)?};'''
assert old in buys;buys=buys.replace(old,new,1)
s=head+buys;f.write_text(s)
(P/'STAGING01.json').write_text(json.dumps({'base':str(base),'source':str(dest),'trade_v3_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'scope':'Real V3 buy/exact accounting helper and selected quote-fee snapshot; accepted Sell order retained.','original_calls':['0x838a0','0x83a50','0x83bb0','0x1485c8','0x149720','0x149b68','0x14a030'],'trial_calls':['buy','buy_exact'],'unrestored':'Original continuation call chain remains isolated prior research; no synthetic callsites.'},indent=2)+'\n')
print(dest)
