from pathlib import Path
import shutil,hashlib,json
P=Path(__file__).parent;src=P/'source';base=P.parent/'parallel-main-v3-validity/byte-source';assert not src.exists();shutil.copytree(base,src)
f=src/'src/trade_v3.rs';s=f.read_text()
old='fn net_quote(spend:u64,pb:u64,cb:u64)->Result<u64>{let total=pb.checked_add(cb).ok_or(PumpError::Overflow)?;let mut quote=narrow(spend as u128*10000/(10000u128+total as u128))?;if quote>0 && add(add(quote,fee(quote,pb)?)?,fee(quote,cb)?)?>spend{quote-=1;}Ok(quote)}'
new='''#[inline(never)]
pub fn net_quote(creator:&Pubkey,pb:u64,cb:u64,spend:u64)->Result<(u64,u64,u64,u64,u64)> {
    let creator_bps=if *creator==Pubkey::default(){0}else{cb};
    let total=pb.checked_add(creator_bps).ok_or(PumpError::Overflow)?;
    let mut quote=spend;
    let mut protocol_fee=0;
    let mut creator_fee=0;
    if total!=0 {
        quote=(spend as u128*10000/(10000u128+total as u128)) as u64;
        require!(quote>0,PumpError::BuyNotEnoughSolToCoverFees);
        protocol_fee=fee(quote,pb)?;
        creator_fee=fee(quote,creator_bps)?;
        let excess=quote.saturating_add(protocol_fee).saturating_add(creator_fee).saturating_sub(spend);
        quote=quote.checked_sub(excess).ok_or(PumpError::BuyNotEnoughSolToCoverFees)?;
        require!(quote>0,PumpError::BuySlippageBelowMinTokensOut);
    }
    Ok((quote,protocol_fee,creator_fee,pb,cb))
}'''
assert s.count(old)==1;s=s.replace(old,new)
start=s.index('pub fn buy_exact_quote(');end=s.index('\nfn read_config(',start);part=s[start:end]
old='''    let quote_budget=net_quote(available,fees.protocol_fee_bps,creator_bps)?;
    require_gt!(available as u128*10000/(10000u128+fees.protocol_fee_bps as u128+creator_bps as u128),0,PumpError::BuyNotEnoughSolToCoverFees);
    require_gt!(quote_budget,0,PumpError::BuySlippageBelowMinTokensOut);'''
new='''    let (quote_budget,initial_protocol_fee,initial_creator_fee,protocol_fee_bps,selected_creator_bps)=net_quote(&curve.creator,fees.protocol_fee_bps,fees.creator_fee_bps,available)?;
    let creator_bps=if curve.creator==Pubkey::default(){0}else{selected_creator_bps};'''
assert part.count(old)==1;part=part.replace(old,new)
old='''    let fee_quote=if exceeds{quote}else{narrow(available as u128*10000/(10000u128+fees.protocol_fee_bps as u128+creator_bps as u128))?};
    let protocol_fee=fee(fee_quote,fees.protocol_fee_bps)?;
    let creator_fee=fee(fee_quote,creator_bps)?;'''
new='''    let protocol_fee=if exceeds{fee(quote,protocol_fee_bps)?}else{initial_protocol_fee};
    let creator_fee=if exceeds{fee(quote,creator_bps)?}else{initial_creator_fee};'''
assert part.count(old)==1;part=part.replace(old,new)
old='''    let estimated_post_quote=if crossing{net_quote(sub(available,first_cost)?,fees.protocol_fee_bps,creator_bps)?}else{0};'''
new='''    let (estimated_post_quote,post_protocol_raw,post_creator_raw)=if crossing {
        let remaining=sub(available,first_cost)?;
        let total=protocol_fee_bps.checked_add(creator_bps).ok_or(PumpError::Overflow)?;
        let nominal=remaining as u128*10000/(10000u128+total as u128);
        if nominal<2 {(0,0,0)}else{
            let (quote,protocol_fee,creator_fee,_,_)=net_quote(&curve.creator,protocol_fee_bps,selected_creator_bps,remaining)?;
            (quote,protocol_fee,creator_fee)
        }
    }else{(0,0,0)};'''
assert part.count(old)==1;part=part.replace(old,new)
old='''    let post_fee_quote=if crossing{narrow(sub(available,first_cost)? as u128*10000/(10000u128+fees.protocol_fee_bps as u128+creator_bps as u128))?}else{0};
    let post_protocol_raw=fee(post_fee_quote,fees.protocol_fee_bps)?;let post_creator_raw=fee(post_fee_quote,creator_bps)?;
'''
assert part.count(old)==1;part=part.replace(old,'')
# Carry preserved returned rate into all later exact-handler calculations/events.
point=part.index('    let creator_bps=if curve.creator==Pubkey::default(){0}else{selected_creator_bps};')
part=part[:point]+part[point:].replace('fees.protocol_fee_bps','protocol_fee_bps').replace('holder_rewards_bps:if curve.is_holder_reward{fees.creator_fee_bps}','holder_rewards_bps:if curve.is_holder_reward{selected_creator_bps}')
s=s[:start]+part+s[end:];f.write_text(s)
(P/'STAGING.json').write_text(json.dumps({'base':str(base),'source':str(src),'owned_file':'src/trade_v3.rs','sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'scope':'Full five-u64 net budget helper with actual initial and continuation V3 calls; preserve original creator-key policy, amounts before one-lamport adjustment, and post-wrapper nominal>=2 gate.'},indent=2)+'\n')
