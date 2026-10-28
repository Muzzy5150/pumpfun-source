"""Run the 28 distinct signed claim CPI/overflow inputs added after Round32."""
from pathlib import Path
import argparse,base64,gzip,hashlib,importlib.util,json
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('claim_compound_cases',P/'probe-compound.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def input_hash(row):
 state={}
 for label,a in row['before'].items():
  if a is None:continue
  address=a.get('address',label);d={n:a[n]for n in ['owner','lamports','executable','rent_epoch']if n in a}
  if 'data_base64'in a:d['data_hex']=base64.b64decode(a['data_base64']).hex()
  elif 'data'in a:d['data_hex']=a['data']
  if address in state:assert state[address]==d
  state[address]=d
 return hashlib.sha256((row['transaction_base64']+json.dumps(state,sort_keys=True,separators=(',',':'))).encode()).hexdigest()
def main():
 parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--candidate');parser.add_argument('--output',type=Path,required=True);a,_=parser.parse_known_args()
 definitions=json.loads((P/'DEDUPLICATED-COMPOUND01.json').read_text())['specs'];assert len(definitions)==28
 base.cases=lambda:(row['case']for row in definitions);base.main()
 report=json.loads(gzip.decompress(a.output.read_bytes()));expected={row['case']['name']:row['input_hash']for row in definitions}
 for row in report['cases']:assert input_hash(row['original'])==expected[row['case']['name']]
 report['driver_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();report['definition_sha256']=hashlib.sha256((P/'DEDUPLICATED-COMPOUND01.json').read_bytes()).hexdigest();report['all_deduplicated_input_hashes_match']=True
 a.output.write_bytes(gzip.compress(json.dumps(report).encode(),mtime=0))
if __name__=='__main__':main()
