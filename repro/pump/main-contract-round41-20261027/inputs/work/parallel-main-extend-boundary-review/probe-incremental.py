"""Twelve new extension inputs including explicit zero-cost Rent configurations."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json
P=Path(__file__).resolve().parent

def load(name,file):
 s=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--output',type=Path,required=True);a,_=parser.parse_known_args()
 normal=load('extend_log_overlay','probe-logs.py');zero=load('extend_zero_rent','probe-zero-rent.py');plain_run=normal.f.run
 specs=json.loads((P/'INCREMENTAL-SPECS.json').read_text())['cases'];assert len(specs)==12;by_name={r['case']['name']:r for r in specs}
 normal.f.run=lambda c,binary=normal.f.ORIGINAL:zero.run(c,binary)if by_name[c['name']]['mode']=='zero-rent'else plain_run(c,binary)
 normal.cases=lambda:(r['case']for r in specs);normal.main()
 d=json.loads(gzip.decompress(a.output.read_bytes()))
 for row in d['cases']:
  c=row['case'];o=row['original'];identity={'transaction_base64':o['transaction_base64'],'before':{k:v for k,v in o['before'].items()if v is not None},'rent':{'lamports_per_byte_year':c.get('rent_lamports_per_byte',3480),'exemption_threshold':c.get('rent_threshold',2.0),'burn_percent':50}}
  h=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest();assert h==by_name[c['name']]['input_hash']
  row['explicit_rent_config']=identity['rent']
 assert not d['mismatches']and not d['diagnostics']['mismatches'];d['definition_sha256']=hashlib.sha256((P/'INCREMENTAL-SPECS.json').read_bytes()).hexdigest();d['driver_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();d['all_original_input_hashes_match']=True
 a.output.write_bytes(gzip.compress(json.dumps(d).encode(),mtime=0))
if __name__=='__main__':main()
