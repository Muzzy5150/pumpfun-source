"""Run frozen relevant corpora against a newly built isolated candidate."""
from pathlib import Path
import argparse,concurrent.futures,gzip,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'scripts'))
from pump_diagnostic_audit import audit
P=argparse.ArgumentParser();P.add_argument('--candidate',type=Path,required=True);P.add_argument('--output-prefix',required=True);P.add_argument('--mode',choices=['focused','full'],required=True);A=P.parse_args();C=A.candidate.resolve()
FOCUSED=[('legacy-boundary','work/parallel-main-buyback-split/probe-legacy-boundary.py'),('low-lamports','work/parallel-main-legacy-buyback-split/probe-sell-low-lamports.py'),('partial-balance','work/parallel-main-legacy-buyback-split/probe-sell-partial-balance.py'),('thresholds','work/parallel-main-legacy-buyback-split/probe-sell-payment-thresholds.py'),('creator-order','work/parallel-main-legacy-buyback-split/probe-sell-creator-order02.py')]
FULL=[('regression','work/parallel-main-fee-accounting/validate.py'),('order','work/parallel-main-buy-v2-order/probe.py'),('sell-expanded','work/parallel-main-sell-v2-buyback/probe-expanded.py'),('sell-atas','work/parallel-main-sell-v2-buyback/probe-atas.py'),('sell-prepare','work/parallel-main-sell-v2-buyback/probe-prepare.py'),('recipients','work/parallel-main-fee-recipient-helper/probe.py'),('boundaries','work/parallel-main-fee-accounting/probe-boundaries.py'),('crossing','work/parallel-main-fee-waiver/crossing.py'),('waiver','work/parallel-main-global-fee-waiver/probe-v2.py'),('payment','work/parallel-main-buy-native-recipient/probe-payment-order.py')]
def run(x):
 name,script=x;prefix=HERE/(A.output_prefix+'-'+name);out=prefix.with_suffix('.json.gz');log=prefix.with_suffix('.log');args=[sys.executable,str(ROOT/script),'--candidate',str(C),'--output',str(out)]
 if name=='waiver':args=[sys.executable,str(ROOT/'work/parallel-main-loader-optimized/pump_with_captured_loader.py'),'--receipt',str(prefix.with_suffix('.loader.json'))]+args[1:]
 with log.open('w') as f:res=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
 if not out.exists():return {'suite':name,'returncode':res.returncode,'archive_missing':True,'log':str(log)}
 data=json.load(gzip.open(out,'rt'));suites=data.get('suites') or {name:data['cases']};diag=audit(suites);rows=[r for values in suites.values() for r in values]
 failures=[r['case'].get('name') for r in rows if r.get('different_fields')];stats={'suite':name,'returncode':res.returncode,'case_count':len(rows),'strict_case_count':diag['log_bearing_cases'],'mismatches':failures,'strict_mismatches':diag['mismatches'],'archive':str(out.relative_to(ROOT)),'archive_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'script':script,'script_sha256':hashlib.sha256((ROOT/script).read_bytes()).hexdigest(),'diagnostics':diag}
 if name=='waiver':stats['loader_receipt']=str(prefix.with_suffix('.loader.json').relative_to(ROOT))
 else:stats['captured_loads']=sum(len(r.get('loader',[])) for r in rows)
 print(json.dumps({k:v for k,v in stats.items() if k not in ['diagnostics','strict_mismatches']})+' strict_failures='+str(len(diag['mismatches'])),flush=True)
 return stats
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,FOCUSED if A.mode=='focused' else FULL))
report={'candidate':str(C.relative_to(ROOT)),'candidate_sha256':hashlib.sha256(C.read_bytes()).hexdigest(),'mode':A.mode,'results':results,'cases':sum(x.get('case_count',0) for x in results),'strict_cases':sum(x.get('strict_case_count',0) for x in results)}
(HERE/(A.output_prefix+'-summary.json')).write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(any(x.get('archive_missing') or x.get('returncode') or x.get('mismatches') or x.get('strict_mismatches') for x in results))
