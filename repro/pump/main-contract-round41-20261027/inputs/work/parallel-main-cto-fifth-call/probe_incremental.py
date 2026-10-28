"""Eighteen deduplicated AdminCto collection-boundary regression inputs."""
from pathlib import Path
import argparse,base64,gzip,hashlib,importlib.util,json,sys
P=Path(__file__).resolve().parent;R=P.parents[1]
def module(name,file):
 s=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=module('base_collection_boundary',P/'probe_collection_boundary.py');wsol=module('wsol_collection_boundary',P/'probe_wsol_boundary.py')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 definitions={r['name']:r['input_hash']for r in json.loads((P/'incremental-cases01.json').read_text())['cases']};assert len(definitions)==18
 rows=[]
 for c in [*base.cases(),*wsol.selected]:
  if c['name']not in definitions:continue
  o,n=base.f.run(c),base.f.run(c,a.candidate)
  identity=hashlib.sha256(json.dumps({'transaction_base64':o['transaction_base64'],'before':{k:v for k,v in o['before'].items()if v is not None}},sort_keys=True,separators=(',',':')).encode()).hexdigest();assert identity==definitions[c['name']]
  assert o['transaction_base64']==n['transaction_base64']
  for v in [o,n]:assert all(base.VersionedTransaction.from_bytes(base64.b64decode(v['transaction_base64'])).verify_with_results())
  differences=[k for k in ['before','after','error','events','inner','return']if o[k]!=n[k]]
  logs=lambda x:[s for s in x['logs']if s.startswith('Program log:')]
  rows.append({'case':c,'original':o,'candidate':n,'different_fields':differences,'program_log_difference':logs(o)!=logs(n)});print(c['name'],differences,logs(o)==logs(n),flush=True)
 assert len(rows)==18
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();report={'case_count':18,'cases':rows,'mismatches':[r['case']['name']for r in rows if r['different_fields']or r['program_log_difference']],'inputs_sha256':{str(p):h(p)for p in [Path(__file__),P/'probe_collection_boundary.py',P/'probe_wsol_boundary.py',P/'incremental-cases01.json',a.candidate]}}
 a.output.write_bytes(gzip.compress(json.dumps(report).encode(),mtime=0));assert not report['mismatches'];print({'passed':18})
if __name__=='__main__':main()
