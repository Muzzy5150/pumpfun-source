from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path.cwd();P=R/'work/parallel-main-multihop-native-edge';base=R/'work/parallel-main-integration/round32-draft-source/programs/pump';out=P/'source01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(root):return {str(p.relative_to(root)):sha(p)for p in sorted(root.rglob('*'))if p.is_file()}
before=manifest(base);assert not out.exists();shutil.copytree(base,out);assert before==manifest(base)==manifest(out)
p=out/'src/multi_hop_curve_swap.rs';s=p.read_text();old='system_transfer(a.user.to_account_info(),h.bonding_curve.to_account_info(),amount)?;';new='crate::user_quote_payments::transfer_native(a.system_program.as_ref(),&a.user,h.bonding_curve.as_ref(),amount)?;';assert s.count(old)==1;s=s.replace(old,new)
oldfn='''fn system_transfer<'info>(from: AccountInfo<'info>, to: AccountInfo<'info>, amount: u64) -> Result<()> {
    if amount == 0 { return Ok(()); }
    invoke(&system_instruction::transfer(from.key,to.key,amount), &[from,to])?;
    Ok(())
}
'''
assert s.count(oldfn)==1;s=s.replace(oldfn,'');s=s.replace(',program_error::ProgramError,system_instruction}',',program_error::ProgramError}');p.write_text(s)
(P/'BASE-MANIFEST.json').write_text(json.dumps(before,indent=2)+'\n');(P/'HYPOTHESIS01.json').write_text(json.dumps({'status':'unbuilt genuine caller reuse','baseline':str(base.relative_to(R)),'base_stable_during_copy':True,'original_call':{'site':'0x5e030','caller':'0x5b3b0','target':'0x8df98','native_bytes':1208},'original_abi':{'r2':'raw system AccountInfo','r3':'typed Signer','r4':'typed Account<BondingCurve>','r5':'native amount'},'source_change':'Replace separate raw two-AccountInfo system-transfer path with existing exact typed native helper; remove now-unused old function and import.','source_file':'src/multi_hop_curve_swap.rs','before_sha256':before['src/multi_hop_curve_swap.rs'],'after_sha256':sha(p)},indent=2)+'\n')
(P/'original-call.asm').write_text(subprocess.check_output(['/Users/shawwalters/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump','-d','--no-show-raw-insn','--start-address=0x5dfc0','--stop-address=0x5e058',str(R/'evidence/original/pump/deployed.so')],text=True));print(sha(p))
