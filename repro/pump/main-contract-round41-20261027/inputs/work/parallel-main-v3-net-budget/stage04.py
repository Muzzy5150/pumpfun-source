from pathlib import Path
import shutil,json,hashlib,struct,sys
P=Path(__file__).parent;dst=P/'source04';assert not dst.exists();shutil.copytree(P/'source03',dst)
f=dst/'src/trade_v3.rs';s=f.read_text();a=s.index('#[inline(never)]\npub fn net_quote(');b=s.index('// Token-2022',a)
new='''#[inline(never)]
pub fn net_quote(creator:&Pubkey,pb:u64,cb:u64,spend:u64)->Result<(u64,u64,u64,u64,u64)> {
    let creator_bps=if *creator==Pubkey::default(){0}else{cb};
    let total=pb.checked_add(creator_bps).ok_or(PumpError::Overflow)?;
    let mut quote=spend;
    if total!=0 && spend!=0 {
        quote=(spend as u128*10000/(10000u128+total as u128)) as u64;
    }
    require_gt!(quote,0,PumpError::BuyNotEnoughSolToCoverFees);
    let protocol_fee=crate::legacy_sell::fee_cpi::fee(quote,pb)?;
    let creator_fee=crate::legacy_sell::fee_cpi::fee(quote,creator_bps)?;
    let cost=quote.saturating_add(protocol_fee).saturating_add(creator_fee);
    if cost>spend {
        let excess=cost.saturating_sub(spend);
        quote=quote.checked_sub(excess).ok_or(PumpError::BuyNotEnoughSolToCoverFees)?;
        require_gt!(quote,0,PumpError::BuySlippageBelowMinTokensOut);
    }
    Ok((quote,protocol_fee,creator_fee,pb,cb))
}
'''
f.write_text(s[:a]+new+s[b:])
(P/'CFG-CORRECTION04.json').write_text(json.dumps({'scope':'Successor control correcting actual original branch targets; prior03 kept frozen.','source':'source04/src/trade_v3.rs','source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'original_branches':[{'address':'0x807b8','offset':19,'actual_target':hex(0x807b8+8+19*8),'meaning':'zero total skips only inverse quotient, then common quote positive check'},{'address':'0x807c0','offset':80,'actual_target':hex(0x807c0+8+80*8),'meaning':'zero spend enters6041 handler'},{'address':'0x80858','offset':61,'actual_target':hex(0x80858+8+61*8),'meaning':'zero quote enters6041 handler'},{'address':'0x80988','offset':132,'actual_target':hex(0x80988+8+132*8),'meaning':'cost<=spend enters success;6042 only occurs after excess correction'}],'supersedes':'ABI-TRACE.json zero-fee early-success interpretation only; preserved earlier report for history.','reason':'Original fee calls are unconditional after quote check. Correct both real computation placement and excess-only final guard; no artificial branch padding.'},indent=2)+'\n')
