from pathlib import Path
import json,hashlib,shutil
r=Path.cwd();p=r/'work/parallel-main-create-gate-order';base=r/'work/parallel-main-integration/round26-source/programs/pump';s=p/'source01';assert not s.exists();shutil.copytree(base,s);f=s/'src/create_v2.rs';v=f.read_text();old=''' let a=&ctx.accounts;
 require_eq!(a.global.create_v2_enabled,true,PumpError::CreateV2Disabled);
 require!(!is_cashback_enabled.0,PumpError::CashbackDeprecated);
 // Mayhem-mode gate: requires the admin flag and rejects any quote-mint remaining accounts.
 if is_mayhem_mode {
  require!(a.global.mayhem_mode_enabled,PumpError::MayhemModeDisabled);
  require!(ctx.remaining_accounts.is_empty(),PumpError::MayhemModeQuoteMintNotAllowed);
 }
''';new=''' let a=&ctx.accounts;
 if is_mayhem_mode {
  require_eq!(a.global.mayhem_mode_enabled,true,PumpError::MayhemModeDisabled);
 }
 require_eq!(a.global.create_v2_enabled,true,PumpError::CreateV2Disabled);
 require!(!is_cashback_enabled.0,PumpError::CashbackDeprecated);
''';assert v.count(old)==1;v=v.replace(old,new)
needle=' let fee=if can_configure_fee && creator_fee_bps.0>0 {';insert=''' if is_mayhem_mode && quote_mint!=Pubkey::default() {
  require!(a.global.whitelisted_quote_mints.contains(&quote_mint),PumpError::MayhemModeQuoteMintNotAllowed);
 }
''';assert v.count(needle)==1;v=v.replace(needle,insert+needle);f.write_text(v)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();files=lambda d:{str(x.relative_to(d)):sha(x)for x in sorted(d.rglob('*'))if x.is_file()};a,b=files(base),files(s);assert[k for k in a if a[k]!=b[k]]==['src/create_v2.rs'];(p/'PLAN01.json').write_text(json.dumps({'baseline':str(base),'source':str(s),'baseline_files':a,'source_files':b,'change':'Mayhem enable comparison first; quote policy after quote selection/ATA, limited to unlisted nonnative quote mint. Captured CPI client untouched.','before_cases':44,'evidence':'Original0x1e7c0 handler and two signed fixture cohorts34+10'},indent=2)+'\n');print(sha(f))
m=json.loads((r/'work/parallel-main-create-pool-links/manifest.json').read_text());m += [{'name':'create_gate_order','script':'work/parallel-main-create-gate-order/probe_gates.py','count':34},{'name':'create_control_gate_order','script':'work/parallel-main-create-gate-order/probe_control_gates.py','count':10}];(p/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');(p/'focused-manifest.json').write_text(json.dumps(m[-2:],indent=2)+'\n');print('cases',sum(x['count']for x in m))
