"""Run the frozen recipient cases in the outer captured-loader process."""
from pathlib import Path
import argparse, gzip, hashlib, importlib.util, json, sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from pump_diagnostic_audit import audit
parser = argparse.ArgumentParser()
parser.add_argument('--candidate', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
path = ROOT / 'work/parallel-main-fee-recipient-helper/probe.py'
spec = importlib.util.spec_from_file_location('frozen_recipient_cases', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.init()
rows = [module.run((name, case, str(args.candidate.resolve()))) for name, case in module.cases()]
diagnostics = audit({'recipient_order': rows})
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
result = {'scope': __doc__, 'case_count': len(rows), 'candidate_sha256': sha(args.candidate),
          'original_sha256': sha(ROOT / 'evidence/original/pump/deployed.so'),
          'input_sha256': {str(p): sha(p) for p in [path, Path(__file__)]},
          'suites': {'recipient_order': rows}, 'diagnostics': diagnostics,
          'mismatches': [i for i, row in enumerate(rows) if row['different_fields']]}
args.output.write_bytes(gzip.compress(json.dumps(result, separators=(',', ':')).encode(), mtime=0))
print({'cases': len(rows), 'mismatches': len(result['mismatches']), 'diagnostic_mismatches': len(diagnostics['mismatches'])}, flush=True)
assert not result['mismatches'] and not diagnostics['mismatches']
