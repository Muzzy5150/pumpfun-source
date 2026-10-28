"""The original 308 extension inputs with stronger logs and full-corpus metadata."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('extend_full_log_overlay',P/'probe-full-logs.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def metadata(path):
 report=json.loads(gzip.decompress(path.read_bytes()));report['original_sha256']=hashlib.sha256(m.m.f.ORIGINAL.read_bytes()).hexdigest();report['driver_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();assert report['case_count']==308 and not report['mismatches']and not report['diagnostics']['mismatches'];path.write_bytes(gzip.compress(json.dumps(report).encode(),mtime=0));return report
if __name__=='__main__':
 p=argparse.ArgumentParser(add_help=False);p.add_argument('--output',type=Path,required=True);a,_=p.parse_known_args();m.m.main();metadata(a.output)
