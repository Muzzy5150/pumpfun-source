from pathlib import Path
import shutil,hashlib,json
R=Path.cwd();P=R/'work/parallel-main-user-quote-wrapper';base=P/'source01';dest=P/'source02';assert not dest.exists();shutil.copytree(base,dest)
p=dest/'src/user_quote_payments.rs';s=p.read_text();s=s.replace('use anchor_spl::token_interface::TokenInterface;','use anchor_spl::token_interface::TokenInterface;\nuse crate::trade_types::BondingCurve;')
s=s.replace('    destination: &AccountInfo<\'info>,\n    payer: &Signer<\'info>,\n    system_program: &Program<\'info, System>,','    system_program: &AccountInfo<\'info>,\n    payer: &Signer<\'info>,\n    destination: &Account<\'info, BondingCurve>,')
s=s.replace('''    let accounts = anchor_lang::system_program::Transfer {
        to: destination.clone(),
        from: payer.to_account_info(),
    };
    anchor_lang::system_program::transfer(
        CpiContext::new(system_program.to_account_info(), accounts), amount,
    )''','''    anchor_lang::system_program::transfer(
        CpiContext::new(system_program.clone(), anchor_lang::system_program::Transfer {
            from: payer.to_account_info(),
            to: destination.to_account_info(),
        }), amount,
    )''')
s=s.replace('transfer_native(destination, payer, system_program, amount)','transfer_native(system_program, payer, destination, amount)');p.write_text(s)
for file in ['trade_v3.rs','buy_v2.rs']:
 p=dest/'src'/file;s=p.read_text();s=s.replace('is_sol,a.bonding_curve.as_ref().as_ref(),&a.user,&a.system_program,','is_sol,a.system_program.as_ref(),&a.user,a.bonding_curve.as_ref(),');s=s.replace('native,a.bonding_curve.as_ref().as_ref(),&a.user,&a.system_program,','native,a.system_program.as_ref(),&a.user,a.bonding_curve.as_ref(),');p.write_text(s)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j={'status':'isolated ABI correction based on typed layout and actual original call operands','source':'source02','previous':'source01','evidence':{'layout':'layout.ll','v2':{'curve':320,'user':344,'system':416},'v3':{'curve':40,'user':64,'system':112},'original_wrapper_0x97930':{'r3':'raw System AccountInfo','r4':'Signer reference','stack[-0x1000]':'Account<BondingCurve> reference'},'original_native_0x8df98':{'r2':'raw System AccountInfo','r3':'Signer reference','r4':'Account<BondingCurve> reference','r5':'amount'}},'hashes':{f:sha(dest/f)for f in ['src/user_quote_payments.rs','src/trade_v3.rs','src/buy_v2.rs','Cargo.lock']},'corrects':'Initial HYPOTHESIS01 labels exchanged native system and curve positions; those source01 semantics were self-consistent but did not reconstruct native ABI.'}
(P/'HYPOTHESIS02.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j['hashes'],indent=2))
