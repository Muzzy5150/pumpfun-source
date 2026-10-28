from pathlib import Path
import argparse,hashlib,json,gzip,subprocess,sys
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;T=R/'work/parallel-main-trading-third';W=R/'work/parallel-main-trading-next';S=R/'work/parallel-main-trading';sys.path.insert(0,str(S))

def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.build=a.build.resolve();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False);candidate=a.build/'candidate.so';receipt=json.loads((a.build/'build-comparison.json').read_text());assert receipt['source_unchanged'] and receipt['returncode']==0;assert hashlib.sha256(candidate.read_bytes()).hexdigest()==receipt['comparison']['candidate_sha256']
 for name,digest in receipt['source_sha256'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==digest,name
 source=T/'source-v4/programs/pump'
 tests=[('native_completion_62',W/'probe_native_completion.py'),('v3_post_edges_27',W/'probe_v3_post_edges.py'),('v3_post_fees_32',W/'probe_v3_post_fees_cli.py'),('v3_post_state_12',W/'probe_v3_post_state.py'),('new_v2_66',S/'probe_v2.py'),('new_v2_fees_151',S/'fee_corpus.py'),('new_route_holder_64',S/'route_probe.py'),('buy_v2',R/'scripts/pump_buy_v2_differential.py'),('sell_v2',R/'scripts/pump_sell_v2_differential.py'),('legacy_buy',R/'scripts/pump_legacy_buy_differential.py'),('legacy_sell_configured',R/'scripts/pump_legacy_sell_configured_fee_differential.py'),('exact_quote_v3',R/'scripts/pump_exact_quote_differential.py'),('v3_extensions',R/'scripts/pump_v3_token_extensions_differential.py'),('buy_v3',R/'scripts/pump_validate_buy.py'),('sell_v3',R/'scripts/pump_validate_sell.py'),('quote_v3',R/'scripts/pump_validate_quote.py'),('legacy_sell',R/'scripts/pump_legacy_sell_differential.py'),('v3_configured',R/'scripts/pump_v3_configured_fee_differential.py'),('native_route_56',R/'repro/pump/native-curve-partial-fortyeight/harness/pump_multi_hop_curve_differential.py'),('selector_72',W/'probe_quote_selector.py'),('quote_origins_12',W/'probe_quote_origins.py'),('native_quote_3',W/'probe_native_quote.py'),('context_failures_24',W/'probe_context_failures.py'),('creator_gate_120',W/'verify_creator_gate.py'),('completion_92',W/'compare_saved_completions.py'),('completion_edges_27',W/'probe_completion_edges.py'),('completion_fuzz_120',W/'fuzz_completion.py'),('old_fences_46',S/'probe_remaining_fences.py')]
 tests += [('token_extensions_36',T/'probe_extensions.py'),('token_extension_edges_416',T/'probe_extension_edges.py'),('buyback_allocation_54',T/'probe_buyback_allocation.py'),('extension_order_68',T/'probe_extension_order.py'),('origin_kinds_38',T/'probe_origin_kinds.py'),('unknown_tlv_50',T/'probe_unknown_tlv.py')]
 rows=[]
 for name,script in tests:
  out=a.output/(name+'.json.gz');cmd=[sys.executable,str(script),'--candidate',str(candidate),'--output',str(out)]
  if name in ['buy_v3','sell_v3','quote_v3']:cmd += ['--source-directory',str(source)]
  if name=='completion_edges_27':cmd += ['--compute-unit-limit','600000']
  with (a.output/(name+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT)
  d=None
  if out.exists():
   raw=out.read_bytes();d=json.loads(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw)
  bad=None if d is None else d.get('mismatches',[i for i,x in enumerate(d.get('cases',[])) if x.get('mismatches',x.get('different_fields'))])
  row={'name':name,'returncode':r.returncode,'case_count':None if d is None else d.get('case_count',len(d.get('cases',[]))),'mismatches':bad};rows.append(row);print(row,flush=True);(a.output/'summary.json').write_text(json.dumps({'candidate_sha256':receipt['comparison']['candidate_sha256'],'suites':rows},indent=2)+'\n')
 import route_fixture as h
 route=[]
 for name,sell,amount,mode,limit in h.fixtures():
  o=h.invoke(sell,amount,mode,limit);b=h.invoke(sell,amount,mode,limit,candidate);diff=[k for k in ['error','events','inner','return_data','before','after','pump_calls','token_calls'] if o[k]!=b[k]];route.append({'case':name,'original':o,'candidate':b,'different_fields':diff})
 (a.output/'two_curve_20.json.gz').write_bytes(gzip.compress(json.dumps({'cases':route},separators=(',',':')).encode(),mtime=0));rows.append({'name':'two_curve_20','returncode':0,'case_count':len(route),'mismatches':[i for i,r in enumerate(route) if r['different_fields']]})
 summary={'candidate_sha256':receipt['comparison']['candidate_sha256'],'suite_count':len(rows),'case_count':sum(x['case_count'] or 0 for x in rows),'suites':rows,'failed_suites':[x['name'] for x in rows if x['returncode'] or x['mismatches']]};(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary,flush=True);subprocess.run([sys.executable,str(T/'audit_results.py'),str(a.output)],check=True)
if __name__=='__main__':main()
