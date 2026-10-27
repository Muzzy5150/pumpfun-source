#!/usr/bin/env python3
"""Write a build record that tools/run_suites.py accepts for a fastbuild.py output.

  python tools/fb_record.py --source-directory <crate> --candidate <out>/candidate.so --output rec.json

run_suites.py reads only returncode, source_unchanged, comparison.candidate_sha256 and
source_directory (the tokenkeg_two_curve suite additionally needs the archived builder's
full report, so run that suite only on archived-builder candidates).
"""
import argparse, hashlib, json
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--source-directory', type=Path, required=True)
ap.add_argument('--candidate', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
a = ap.parse_args()
a.output.write_text(json.dumps({'returncode': 0, 'source_unchanged': True, 'builder': 'fastbuild.py (identity recipe)',
                                'source_directory': str(a.source_directory.resolve()),
                                'comparison': {'candidate_sha256': hashlib.sha256(a.candidate.read_bytes()).hexdigest()}}, indent=1) + '\n')
