"""The34 distinct signed QuoteControl reader inputs absent from accepted R34."""
from pathlib import Path
import argparse,base64,gzip,hashlib,importlib.util,json,sys
P=Path(__file__).resolve().parent;R=P.parents[1]
spec=importlib.util.spec_from_file_location('quote_control_reader_cases',P/'probe-reader.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
sys.path.insert(0,str(R/'scripts'))
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction
def input_hash(v):
 return hashlib.sha256(json.dumps({'transaction_base64':v['transaction_base64'],'before':{k:x for k,x in v['before'].items()if x is not None}},sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 selection={r['case']:r['input_hash']for r in json.loads((P/'DEDUP01.json').read_text())['records']if r['new']};assert len(selection)==34
 rows=[]
 for c in fixture.cases():
  if c['case']not in selection:continue
  o,n=fixture.f.run(c),fixture.f.run(c,a.candidate)
  assert input_hash(o)==selection[c['case']]
  assert o['transaction_base64']==n['transaction_base64']
  for side in [o,n]:assert all(VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
  diff=[k for k in ['before','after','error','events','inner','return']if o[k]!=n[k]]
  rows.append({'case':c,'original':o,'candidate':n,'different_fields':diff});print(c['case'],diff,flush=True)
 assert len(rows)==34
 diagnostic=audit({'reader_incremental':rows});h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 report={'scope':__doc__,'case_count':len(rows),'candidate_sha256':h(a.candidate),'original_sha256':h(fixture.f.ORIGINAL),'script_sha256':h(Path(__file__)),'fixture_sha256':h(P/'probe-reader.py'),'selection_sha256':h(P/'DEDUP01.json'),'cases':rows,'mismatches':[r['case']['case']for r in rows if r['different_fields']],'diagnostics':diagnostic}
 a.output.write_bytes(gzip.compress(json.dumps(report).encode(),mtime=0));assert not report['mismatches']and not diagnostic['mismatches'];print({'passed':34})
if __name__=='__main__':main()
