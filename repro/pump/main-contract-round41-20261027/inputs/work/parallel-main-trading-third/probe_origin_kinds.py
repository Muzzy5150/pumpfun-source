from pathlib import Path
import argparse,json,gzip,sys,hashlib
from audit_results import messages
W=Path(__file__).resolve().parent;R=W.parents[1];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'work/parallel-main-trading-next'))
import quote_extra_fixture as q
import pump_buy_v2_differential as v2
import pump_legacy_buy_differential as legacy

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for r in json.loads((W/'trading-origin-baseline.json').read_text()):
  group=r['path'].split('/')[0];c=dict(r['case'])
  if group in ['legacy_buy','buy_v2']:
   fn=legacy.run if group=='legacy_buy' else v2.run;o=fn(c);b=fn(c,a.candidate)
  else:
   c['operation']=c.get('operation',{'buy':'buy_v3','sell':'sell_v3','quote':('buy_v3' if c.get('kind')=='buy' else 'sell_v3'),'exact_quote_v3':'buy_exact_quote_in_v3'}.get(group))
   if 'max_cost' not in c:c['max_cost']=c.get('min_output',0)
   if group=='quote':c['token_quote']=True
   o=q.run(R/'evidence/original/pump/deployed.so',c);b=q.run(a.candidate,c)
  om,bm=messages(o['logs']),messages(b['logs']);diff=[] if om==bm else ['diagnostics'];rows.append({'path':r['path'],'case':c,'original':o,'candidate':b,'different_fields':diff});print(r['path'],om['origins'],bm['origins'],diff,flush=True)
 a.output.write_bytes(gzip.compress(json.dumps({'case_count':len(rows),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']]},separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':main()
