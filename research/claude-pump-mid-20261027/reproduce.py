#!/usr/bin/env python3
"""Rebuild the pump-mid lane candidate: Round26 primary source plus this packet's source files.

The Round26 archived primary source is copied to a staging crate, the base hashes of every
replaced file are checked against the Round26 checkpoint, the packet's full source files
are copied over (they equal Round26 + patches/*.patch), and the unchanged repository
builder `scripts/pump_build_verified.py` compiles it with the authentic workspace layout.
Original executable bytes are never compiler inputs.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys

P = Path(__file__).resolve().parent
ROOT = next(p for p in P.parents if (p / 'evidence/original/pump/deployed.so').is_file())
BASE = ROOT / 'repro/pump/main-contract-round26-20261027'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--registry-home', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True, help='new directory under the repository root')
    ap.add_argument('--dependency-cache', type=Path)
    a = ap.parse_args()
    rec = json.loads((P / 'CANDIDATE.json').read_text())
    cp = json.loads((BASE / 'CHECKPOINT.json').read_text())
    out = a.output.resolve(); out.relative_to(ROOT)
    stage = out.with_name(out.name + '.source') / 'pump'
    assert not stage.parent.exists(), f'{stage.parent} exists'
    shutil.copytree(BASE / 'primary', stage)
    for name, digest in cp['primary_source_sha256'].items():
        assert sha(stage / name) == digest, ('Round26 primary differs', name)
    for name, change in rec['changed_files'].items():
        target = stage / name
        if change['base_sha256'] is None:
            assert not target.exists(), name
        else:
            assert sha(target) == change['base_sha256'], ('unexpected base', name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(P / 'source/programs/pump' / name, target)
        assert sha(target) == change['sha256'], ('packet file differs', name)
    cmd = [sys.executable, str(ROOT / 'scripts/pump_build_verified.py'), '--source-directory', str(stage),
           '--workspace-layout', '--registry-home', str(a.registry_home.resolve()), '--output', str(out)]
    if a.dependency_cache:
        cmd += ['--dependency-cache', str(a.dependency_cache.resolve())]
    subprocess.run(cmd, check=True, cwd=ROOT)
    report = json.loads((out / 'build-comparison.json').read_text())
    assert report['comparison']['candidate_sha256'] == rec['candidate_sha256'], report['comparison']['candidate_sha256']
    assert report['unstripped_sha256'] == rec['unstripped_sha256'], report['unstripped_sha256']
    print('Reproduced both pump-mid lane ELF hashes:', rec['candidate_sha256'], rec['unstripped_sha256'])


if __name__ == '__main__':
    main()
