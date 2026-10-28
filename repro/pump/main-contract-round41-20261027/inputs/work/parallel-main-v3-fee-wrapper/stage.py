from pathlib import Path
import shutil,json,hashlib
P=Path(__file__).parent;src=P/'source';base=P.parent/'parallel-main-v3-sell-supply/source';assert not src.exists();shutil.copytree(base,src)
f=src/'src/trade_v3.rs';s=f.read_text()
a=s.index('fn selected(');b=s.index('/// Validate the shared curve flags',a)
helper='''pub fn select_fee_rates(tiers:&[crate::trade_types::FeeTier],cap:u128)->Result<(u64,u64)> {
    let first=tiers.first().ok_or_else(||error!(PumpError::FeeTiersEmpty))?;
    let tier=if cap<first.market_cap_lamports_threshold {first}else{
        tiers.iter().rev().find(|t|t.market_cap_lamports_threshold<=cap).unwrap_or(first)
    };
    Ok((tier.fees.protocol_fee_bps,tier.fees.creator_fee_bps))
}

pub fn selected_trade_fees(global:&Global,curve:&BondingCurve,config:&FeeConfig,data_len:usize,cap:u128,quote:u64)->Result<(u64,u64,u64,u64)> {
    require!(data_len>=2512,PumpError::FeeConfigTooShort);
    let quote_mint=curve.quote_mint;
    let (protocol_bps,selected_creator_bps)=if quote_mint==Pubkey::default() || quote_mint==WSOL || quote_mint==QUOTE_2 {
        select_fee_rates(&config.fee_tiers,cap)?
    }else if quote_mint==USDC {
        select_fee_rates(if data_len>4072{&config.stable_fee_tiers}else{&[]},cap)?
    }else{
        let exotic=&config.exotic_flat_fees;
        let fees=if data_len>4096 && (exotic.lp_fee_bps!=0 || exotic.protocol_fee_bps!=0 || exotic.creator_fee_bps!=0) {exotic}else{&config.flat_fees};
        (fees.protocol_fee_bps,fees.creator_fee_bps)
    };
    let creator_bps=if global.creator_fee_configurable && curve.creator_fee_bps>0 {curve.creator_fee_bps}else{selected_creator_bps};
    let protocol_fee=crate::legacy_sell::fee_cpi::fee(quote,protocol_bps)?;
    let creator_fee=if curve.creator==Pubkey::default(){0}else{crate::legacy_sell::fee_cpi::fee(quote,creator_bps)?};
    Ok((protocol_fee,creator_fee,protocol_bps,creator_bps))
}

pub fn trade_fees(a:&SellV3,quote:u64)->Result<(u64,u64,u64,u64)> {
    if a.user.key()==a.global.whitelist_pda {return Ok((0,0,0,0));}
    let config_info=a.fee_config.to_account_info();
    let data_len=config_info.data_len();
    let cap=buy_fee_market_cap(&a.bonding_curve,&a.base_mint)?;
    selected_trade_fees(&a.global,&a.bonding_curve,&a.fee_config.0,data_len,cap,quote)
}

'''
s=s[:a]+helper+s[b:]
starts=[('pub fn sell(', 'pub fn buy('),('pub fn buy(', 'pub fn buy_exact_quote('),('pub fn buy_exact_quote(', '\nfn read_config(')]
for begin,end in starts:
 a=s.index(begin);b=s.index(end,a);part=s[a:b]
 c=part.index('    let (fees,creator_bps)=')
 if begin.startswith('pub fn buy_exact'):
  d=part.index('    let quote_budget=',c)
  replacement='    let (_,_,protocol_fee_bps,creator_fee_bps)=trade_fees(a,available)?;\n    let creator_bps=if curve.creator==Pubkey::default(){0}else{creator_fee_bps};\n'
 else:
  d=part.index('    let buyback_bps=',c)
  replacement='    let (protocol_fee,creator_fee,protocol_fee_bps,creator_fee_bps)=trade_fees(a,quote)?;\n'
  if begin.startswith('pub fn buy('):replacement+='    let creator_bps=if curve.creator==Pubkey::default(){0}else{creator_fee_bps};\n'
 part=part[:c]+replacement+part[d:]
 part=part.replace('fees.protocol_fee_bps','protocol_fee_bps').replace('fees.creator_fee_bps','creator_fee_bps')
 s=s[:a]+part+s[b:]
a=s.index('\nfn read_config(');b=s.index('\nconst QUOTE_2:',a);s=s[:a]+s[b:]
f.write_text(s)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();(P/'STAGING.json').write_text(json.dumps({'base':str(base),'source':str(src),'owned_changes':['src/trade_v3.rs'],'source_sha256':sha(f),'wrapper_target':'0x7fde8/1040','selector_target':'0x89ec8/1640','tier_target':'0x89b48/896','original_wrapper_calls':['0x82ff0','0x148308','0x149018','0x149a18','0x14af28'],'original_selector_calls':['0x581c8','0x5cdb8','0x5cef8','0x80180'],'scope':'Reuse typed decoded FeeConfig; preserve real AccountInfo clone/data_len/drop, whitelist-before-query, mode-selected cap, fee evaluation order and original4-u64 outputs. No shared fee math edits, no artificial coordinates.'},indent=2)+'\n')
