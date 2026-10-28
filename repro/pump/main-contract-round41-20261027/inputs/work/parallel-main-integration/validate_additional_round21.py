"""Replay focused recovery corpora and new account/admin boundary cases against the composed main-Pump candidate."""
from pathlib import Path
import argparse,ast,concurrent.futures,gzip,hashlib,json,subprocess,sys,traceback
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;T=ROOT/'work/parallel-main-trading-third';N=ROOT/'work/parallel-main-trading-next';S=ROOT/'work/parallel-main-trading'
sys.path.insert(0,str(ROOT/'scripts'));from pump_diagnostic_audit import audit
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b.startswith(b'\x1f\x8b')else b)
def main():
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,choices=range(1,5),default=4);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--source-directory',type=Path,required=True);p.add_argument('--build-comparison',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.candidate=a.candidate.resolve();a.output=a.output.resolve()
 record=read(a.build_comparison);assert record['returncode']==0 and record['source_unchanged'] and sha(a.candidate)==record['comparison']['candidate_sha256'];assert all(sha(ROOT/k)==v for k,v in record['source_sha256'].items())
 env={'R':ROOT,'S':S,'W':N,'T':T};fn=next(x for x in ast.parse((T/'verify_candidate.py').read_text()).body if isinstance(x,ast.FunctionDef)and x.name=='main');tests=[]
 for node in fn.body:
  if isinstance(node,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='tests'for x in node.targets):tests=eval(compile(ast.Expression(node.value),'<known-suite-list>','eval'),env)
  elif isinstance(node,ast.AugAssign)and isinstance(node.target,ast.Name)and node.target.id=='tests':tests+=eval(compile(ast.Expression(node.value),'<known-suite-list>','eval'),env)
 skip={'buy_v2','sell_v2','legacy_buy','legacy_sell_configured','exact_quote_v3','buy_v3','sell_v3','quote_v3','legacy_sell','v3_configured','native_route_56'}
 previous=read(T/'final-validation-parallel-02/summary.json');counts={r['name']:r['case_count']for r in previous['suites']};tests=[(n,s,counts[n])for n,s in tests if n not in skip]
 tests += [('root_legacy_layouts',ROOT/'work/parallel-main-context2/migration_partial_layouts.py',27),('root_v2_layouts',ROOT/'work/parallel-main-context2/migration_v2_partial_layouts.py',54),('root_v2_bool_layouts',ROOT/'work/parallel-main-context2/migration_v2_decoder_boundaries.py',24),('root_account_origins',ROOT/'work/parallel-main-origins/compare_origins.py',47),('accounts_zero_payout',ROOT/'work/parallel-main-accounts/admin_cto_zero_token_payout.py',36),('accounts_contexts',ROOT/'work/parallel-main-accounts/account_context_probe.py',23),('scheduler_577',ROOT/'work/parallel-main-incentives/check-scheduler-final.py',577),('claim_grid_132',W/'claim_grid_cli.py',132),('authority_19',ROOT/'work/parallel-main-coverage/capture_authority_receipts.py',19)]
 tests += [('v3_context_39',ROOT/'work/parallel-main-trading-contexts/probe_v3_context.py',39),('v3_buy_boundaries_28',ROOT/'work/parallel-main-trading-contexts/probe_v3_buy_boundaries.py',28),('buyback_recipients_100',ROOT/'work/parallel-main-buyback-recipients/check_remaining.py',100),('creator_owner_6',ROOT/'work/parallel-main-creator-owner/check_owner.py',6),('curve_boundaries_64',ROOT/'work/parallel-main-curve-layouts/curve-boundary-probe.py',64)]
 tests += [('v3_continuation_42',ROOT/'work/parallel-main-trading-contexts/probe_v3_continuation.py',42),('v3_post_fees_80',ROOT/'work/parallel-main-trading-contexts/probe_v3_post_fees.py',80),('cashback_program_6',ROOT/'work/parallel-main-cashback-program/check_program.py',6),('claim_program_precedence_20',ROOT/'work/parallel-main-incentives-next/probe_claim_program_precedence.py',20)]
 tests += [('migration_headers',ROOT/'work/parallel-main-migration-quote-reader/check_headers.py',66),('migration_balances',ROOT/'work/parallel-main-migration-preexisting/check_balances.py',7),('cto_frozen',ROOT/'work/parallel-main-cto-frozen/check_frozen.py',32),('cto_edges',ROOT/'work/parallel-main-cto-frozen/check_edges.py',40)]
 tests += [('distribution_regressions_62',W/'distribution_regressions.py',62),('distribution_custom_rent_6',ROOT/'work/parallel-main-minimum-audit/rent-probe.py',6)]
 tests += [('claim_mint_6',ROOT/'work/parallel-main-incentives-next/probe_claim_incentive_mint.py',6),('claim_zero_log_4',ROOT/'work/parallel-main-incentives-next/probe_claim_empty_log.py',4),('legacy_token22_27',ROOT/'work/parallel-main-migration-contexts/token22-verify.py',27),('cto_context_34',W/'cto_regressions.py',34),('admin_context_299',ROOT/'scripts/pump_incentives_admin_differential.py',299)]
 tests += [('trade_optional_bool_115',W/'recovered_trade_probes.py',115),('v2_guards_200',W/'recovered_trade_probes.py',200),('legacy_rent_12',ROOT/'work/parallel-main-legacy-buy-next/probe_rent_available.py',12),('legacy_zero_buyback_8',ROOT/'work/parallel-main-legacy-buy-next/probe_zero_buyback.py',8),('legacy_buyback_order_8',ROOT/'work/parallel-main-legacy-buy-next/probe_buyback_order.py',8),('legacy_partial_zero_8',ROOT/'work/parallel-main-legacy-buy-next/probe_partial_zero.py',8),('legacy_user_authority_4',ROOT/'work/parallel-main-legacy-context/probe_user_authority.py',4),('legacy_user_owner_8',ROOT/'work/parallel-main-legacy-context/probe_user_owner.py',8),('v3_user_constraints_12',ROOT/'work/parallel-main-v3-user-constraints/probe.py',12),('v3_mint_curve_18',ROOT/'work/parallel-main-v3-user-constraints/probe_v2.py',18),('v3_native_buyback_18',ROOT/'work/parallel-main-v3-user-constraints/probe_buyback.py',18),('v3_token_buyback_12',ROOT/'work/parallel-main-v3-user-constraints/probe_buyback_token.py',12)]
 tests += [('v3_precedence_36', ROOT/'work/parallel-main-v3-helpers/probe_precedence_extended.py', 36), ('legacy_sell_rent_12', ROOT/'work/parallel-main-legacy-sell-rent/probe_sell_rent.py', 12), ('v2_creator_rent_80', ROOT/'work/parallel-main-integration/recovered_rent_probes.py', 80), ('v2_curve_rent_8', ROOT/'work/parallel-main-v2-helpers/curve-rent-probe.py', 8), ('v2_zero_fee_8', ROOT/'work/parallel-main-v2-helpers/fee-zero-probe.py', 8)]
 tests += [('cto_rent', ROOT/'work/parallel-main-admin-cto-rent/probe_cto_rent.py', 12), ('cto_fees', ROOT/'work/parallel-main-admin-cto-rent/probe_cto_fees.py', 12), ('migrate_prepare', ROOT/'work/parallel-main-migrate-prepare/probe_migrate_prepare.py', 12), ('migrate_v2_prepare', ROOT/'work/parallel-main-migrate-v2-prepare/probe_prepare.py', 32)]
 tests += [('fee_market_cap', ROOT/'work/parallel-main-integration/recovered_fee_market_probes.py', 206), ('sweep_rent', ROOT/'work/parallel-main-sweep-prepare/probe_native_reserve.py', 12), ('sweep_order', ROOT/'work/parallel-main-sweep-prepare/probe_prepare_edges.py', 20), ('sweep_default_quote', ROOT/'work/parallel-main-sweep-quote-predicate/probe_default_quote.py', 8)]
 tests += [('sharing_config_78',ROOT/'work/parallel-main-decode-envelope/probe_sharing_config.py',78)]

 tests += [('recipient_order_144',W/'recovered_recipient_probes.py',144),('fee_waiver_27',ROOT/'work/parallel-main-global-fee-waiver/probe-v2.py',27),('fee_waiver_crossing_36',ROOT/'work/parallel-main-fee-waiver/crossing.py',36),('sell_v2_buyback_32',ROOT/'work/parallel-main-sell-v2-buyback/probe-expanded.py',32),('sell_v2_atas_25',ROOT/'work/parallel-main-sell-v2-buyback/probe-atas.py',25),('sell_v2_prepare_12',ROOT/'work/parallel-main-sell-v2-buyback/probe-prepare.py',12),('buy_v2_order_130',ROOT/'work/parallel-main-buy-v2-order/probe.py',130),('ancestor_boundaries_68',ROOT/'work/parallel-main-create-frontier/probe_ancestor_boundaries.py',68)]
 tests += [('v3_waiver',ROOT/'work/parallel-main-global-fee-waiver/probe-v3.py',18)]
 tests += [('v3_waiver_order',ROOT/'work/parallel-main-v3-fee-waiver/probe-order.py',18)]
 tests += [('v3_waived_crossing',ROOT/'work/parallel-main-v3-fee-waiver/probe-waived-crossing.py',16)]
 tests += [('v3_crossing_matrix',ROOT/'work/parallel-main-v3-fee-waiver/probe-crossing-matrix.py',12)]
 tests += [('v3_post_ceil_divisible',ROOT/'work/parallel-main-v3-post-ceil/probe.py',12)]
 tests += [('v3_post_ceil_boundaries',ROOT/'work/parallel-main-v3-post-ceil/probe-boundaries.py',12)]
 tests += [('multihop_validity_flags',ROOT/'work/parallel-main-v3-validity/probe_multihop_flags.py',16)]
 tests += [('v3_net_budget',ROOT/'work/parallel-main-v3-net-budget/probe.py',96)]
 tests += [('v3_sell_supply_16',ROOT/'work/parallel-main-v3-net-budget/probe-sell-supply.py',16),('v3_sell_zero_reserve_4',ROOT/'work/parallel-main-v3-sell-supply/probe-zero-reserve.py',4)]
 tests += [('v2_payment_panic_order_64',ROOT/'work/parallel-main-buy-native-recipient/probe-payment-order.py',64),('v3_fee_config_boundaries_144',ROOT/'work/parallel-main-v3-fee-wrapper/probe-config-boundaries.py',144),('v3_continuation_tiers_12',ROOT/'work/parallel-main-v3-fee-wrapper/probe-continuation-tiers.py',12)]
 tests.sort(key=lambda entry:(-entry[2],entry[0]))
 out=a.output.parent/(a.output.name+'.suites');out.mkdir(parents=True,exist_ok=True);suites={};rows=[]
 wrapper=ROOT/'work/parallel-main-loader-optimized/pump_with_captured_loader.py';inputs={str(p):sha(p)for p in [Path(__file__),a.candidate,a.build_comparison,wrapper,wrapper.with_name('pump_captured_loader.py'),ROOT/'scripts/pump_diagnostic_audit.py',T/'verify_candidate.py',T/'final-validation-parallel-02/summary.json',*[s for _,s,_ in tests]]}
 def run(entry):
  name,script,count=entry;result_path=out/(name+'.json.gz');loader_path=out/(name+'.loader.json');cmd=[sys.executable,str(wrapper),'--receipt',str(loader_path),str(script),'--candidate',str(a.candidate),'--output',str(result_path)]
  if "'--source-directory'"in script.read_text()or'"--source-directory"'in script.read_text():cmd+=['--source-directory',str(a.source_directory.resolve())]
  if name=='completion_edges_27':cmd+=['--compute-unit-limit','600000']
  if name=='trade_optional_bool_115':cmd+=['--family','bool']
  if name=='v2_guards_200':cmd+=['--family','v2-guard']
  with(out/(name+'.log')).open('w')as f:r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  r.check_returncode();d=read(result_path);n=d['case_count'] if 'case_count' in d else (d['cases'] if isinstance(d.get('cases'),int) else len(d.get('cases',[])));assert n==count,(name,n,count);assert not d.get('mismatches',[]),name
  def walk(x):
   if isinstance(x,dict):
    for key,val in x.items():
     if key in ['different_fields','differences','mismatches']:assert not val,(name,key,val)
     else:walk(val)
   elif isinstance(x,list):
    for y in x:walk(y)
  walk(d);l=read(loader_path);assert {x['elf_sha256']for x in l['loads']}=={sha(a.candidate),record['comparison']['original_sha256']}
  return name,d,{'name':name,'case_count':n,'script_sha256':sha(script),'result_sha256':sha(result_path),'loader_receipt_sha256':sha(loader_path),'command':cmd}
 errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers)as pool:
  jobs={pool.submit(run,t):t[0] for t in tests}
  for future in concurrent.futures.as_completed(jobs):
   if future.cancelled():continue
   try:name,d,row=future.result()
   except Exception as exc:
    errors.append({'suite':jobs[future],'error':repr(exc),'traceback':traceback.format_exc()});print('failed',jobs[future],repr(exc),flush=True)
    for pending in jobs:pending.cancel()
    continue
   suites[name]=d;rows.append(row);print(name,row['case_count'],flush=True)
 if errors:
  a.output.with_name(a.output.name+'.failed.json').write_text(json.dumps({'complete':False,'completed_suites':list(suites),'errors':errors,'input_sha256':inputs},indent=2)+'\n');raise RuntimeError('suite failure; partial receipts retained')
 assert inputs=={k:sha(Path(k))for k in inputs};assert all(sha(ROOT/k)==v for k,v in record['source_sha256'].items());diagnostics=audit(suites)
 final={'scope':__doc__,'loader_profile':'captured-upgradeable','candidate_sha256':sha(a.candidate),'compiled_source_sha256':record['source_sha256'],'input_sha256':inputs,'suite_count':len(suites),'case_count':sum(x['case_count']for x in rows),'results':rows,'diagnostics':diagnostics,'suites':suites}
 a.output.write_bytes(gzip.compress(json.dumps(final,separators=(',',':')).encode(),mtime=0));print({'suite_count':len(suites),'case_count':final['case_count'],'diagnostic_cases':diagnostics['log_bearing_cases'],'diagnostic_mismatches':len(diagnostics['mismatches'])});assert not diagnostics['mismatches']
if __name__=='__main__':main()
