"""Replay a selected subset of the independently validated creator rent review."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json
P=Path(__file__).resolve().parent

def module(name,file):
 s=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 p=argparse.ArgumentParser(add_help=False);p.add_argument('--cases-file',type=Path);p.add_argument('--output',type=Path);p.add_argument('--list-only',action='store_true');a,unknown=p.parse_known_args()
 records=json.loads((a.cases_file or P/'SPECS01.json').read_text());records=records['cases']if isinstance(records,dict)else records
 if a.list_only:print(json.dumps({'case_count':len(records),'names':[r['case']['name']for r in records]}));return
 assert a.output is not None
 normal=module('collection_normal','probe-precedence.py');executable=module('collection_executable','probe-executable.py');plain_run=normal.run
 normal.run=lambda c,binary=None:executable.run(c,binary)if c.get('actual_executable')else plain_run(c,binary)
 normal.cases=lambda:(r['case']for r in records)
 import sys
 sys.argv=[sys.argv[0],*unknown,'--output',str(a.output)]
 normal.main()
 report=json.loads(gzip.decompress(a.output.read_bytes()));expected={r['case']['name']:r['input_hash']for r in records}
 for row in report['cases']:
  o=row['original'];h=hashlib.sha256((o['transaction_base64']+json.dumps({k:v for k,v in o['before'].items()if v is not None},sort_keys=True,separators=(',',':'))).encode()).hexdigest();assert h==expected[row['case']['name']]
 assert not report['mismatches'] and not report['diagnostics']['mismatches']
 report['driver_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();report['selection_sha256']=hashlib.sha256((a.cases_file or P/'SPECS01.json').read_bytes()).hexdigest();report['all_original_input_hashes_match']=True
 a.output.write_bytes(gzip.compress(json.dumps(report).encode(),mtime=0))
if __name__=='__main__':main()
