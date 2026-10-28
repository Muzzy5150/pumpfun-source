#!/usr/bin/env python3
"""Verify the selected main-Pump source against its sealed, reproduced checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
from build_source_manifest import source_manifest
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'repro/pump/main-contract-round41-20261027'
MANIFEST_SHA256 = '31a50506d8bb3cb7524fe1d0be6244eb8467cb0b31b652b6c53e0606e8e6c438'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root):
    root = Path(root).resolve()
    package = root / PACKAGE
    assert sha(package / 'MANIFEST.json') == MANIFEST_SHA256
    checkpoint = json.loads((package / 'CHECKPOINT.json').read_text())
    status = json.loads((root / 'repro/status.json').read_text())['pump']
    assert status['candidate_artifact'] == PACKAGE + '/candidate.so'
    assert status['candidate_sha256'] == checkpoint['candidate_sha256']
    assert status['symbols_sha256'] == checkpoint['unstripped_sha256']
    assert not status['full_byte_equality'] and not checkpoint['goal_complete']
    for name, expected in checkpoint['primary_source_sha256'].items():
        path = root / 'programs/pump' / name
        assert not path.is_symlink() and sha(path) == expected, name
    compiled_inputs = source_manifest(root / 'programs/pump', root / 'programs/pump', root)
    actual = {str((root / name).relative_to(root / 'programs/pump')) for name in compiled_inputs}
    assert actual == set(checkpoint['primary_source_sha256'])
    subprocess.run([sys.executable, '-B', str(package / 'verify.py')],
                   cwd=root, check=True)
    return {'status': 'PASS', 'program': 'pump',
            'candidate_sha256': checkpoint['candidate_sha256'],
            'source_files': len(actual),
            'normalized_windows': checkpoint['normalized_windows'],
            'original_windows': checkpoint['original_windows'],
            'whole_elf_equal': False, 'goal_complete': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(verify(args.repo), indent=2))
