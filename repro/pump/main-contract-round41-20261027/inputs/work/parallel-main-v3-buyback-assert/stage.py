from pathlib import Path
import shutil,json,hashlib
p=Path(__file__).parent;candidate=Path('work/parallel-main-integration/round21-source/programs/pump');base=candidate if candidate.is_dir()else Path('work/parallel-main-shared-sell-transfer/raw-authority-source');d=p/'source';assert not d.exists();shutil.copytree(base,d);f=d/'src/trade_v3.rs';s=f.read_text();insert='''
fn v3_buyback_split(protocol_fee:u64,buyback_bps:u64)->(u64,u64) {
    let buyback_fee=u64::try_from(protocol_fee as u128*buyback_bps as u128/10000)
        .expect("buyback fee is at most protocol_fee");
    let retained=protocol_fee.checked_sub(buyback_fee)
        .expect("buyback_fee never exceeds protocol_fee");
    (buyback_fee,retained)
}
''';needle='fn selected(';i=s.index(needle);s=s[:i]+insert+s[i:]
for begin,end in [('pub fn sell(','pub fn buy('),('pub fn buy(','pub fn buy_exact_quote('),('pub fn buy_exact_quote(','\nfn read_config(')]:
 a=s.index(begin);b=s.index(end,a);part=s[a:b]
 old='    let buyback_fee=narrow(protocol_fee as u128*buyback_bps as u128/10000)?;\n';assert part.count(old)==1;part=part.replace(old,'')
 if begin=='pub fn sell(':
  old='    let buyback_received=if is_sol{buyback_fee}else{sub(buyback_fee,quote_transfer_fee(&a.quote_mint.to_account_info(),buyback_fee,false)?)?};\n';assert part.count(old)==1;part=part.replace(old,'')
  old='    let retained=sub(protocol_fee,buyback_fee)?;';assert part.count(old)==1;part=part.replace(old,'    let (buyback_fee,retained)=v3_buyback_split(protocol_fee,buyback_bps);\n    let buyback_received=if is_sol{buyback_fee}else{sub(buyback_fee,quote_transfer_fee(&a.quote_mint.to_account_info(),buyback_fee,false)?)?};')
 else:
  old='    let post_buyback=narrow(post_protocol as u128*buyback_bps as u128/10000)?;';assert part.count(old)==1;part=part.replace(old,'    let (buyback_fee,retained)=v3_buyback_split(protocol_fee,buyback_bps);\n    let (post_buyback,post_retained)=v3_buyback_split(post_protocol,buyback_bps);')
  old='    let retained=sub(protocol_fee,buyback_fee)?;\n';assert part.count(old)==1;part=part.replace(old,'');assert part.count('sub(post_protocol,post_buyback)?')==1;part=part.replace('sub(post_protocol,post_buyback)?','post_retained')
 s=s[:a]+part+s[b:]
f.write_text(s);sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();(p/'STAGING.json').write_text(json.dumps({'base':str(base),'source':str(d),'owned_change':'src/trade_v3.rs','source_sha256':sha(f),'scope':'Reproduce originalV3buyback expect payloads and their side-specific order, independent of continuation experiments. No V2/shared fee math edits.','proofs':['before.json.gz:54cases/12mismatches','order-before.json.gz:16cases/8mismatches'],'placement':['buy/exact: afterpool/pricingchecks beforelimit checks','sell: afterslippagecheck']},indent=2)+'\n')
