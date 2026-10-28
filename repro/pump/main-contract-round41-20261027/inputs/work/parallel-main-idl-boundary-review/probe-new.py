"""Replay the ten distinct IDL transfer inputs added by this reconstruction."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('idl_transfer_probe',P/'probe-transfer.py');probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
def main():
 parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--output',type=Path,required=True);a,_=parser.parse_known_args()
 records=json.loads((P/'DEDUP01.json').read_text())['cases'];assert len(records)==10;probe.cases=lambda:(r['case']for r in records);probe.main()
 d=json.loads(gzip.decompress(a.output.read_bytes()));expected={r['case']['name']:r['input_hash']for r in records}
 for row in d['cases']:
  o=row['original'];h=hashlib.sha256((o['transaction_base64']+json.dumps({k:v for k,v in o['before'].items()if v is not None},sort_keys=True,separators=(',',':'))).encode()).hexdigest();assert h==expected[row['case']['name']]
 assert not d['mismatches']and not d['diagnostics']['mismatches'];d['driver_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();d['definition_sha256']=hashlib.sha256((P/'DEDUP01.json').read_bytes()).hexdigest();d['all_input_hashes_match']=True;a.output.write_bytes(gzip.compress(json.dumps(d).encode(),mtime=0))
if __name__=='__main__':main()
