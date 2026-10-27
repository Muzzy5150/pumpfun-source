#!/usr/bin/env python3
"""Rebuild the pump-hi lane candidate and re-measure it against the original.

Materializes the frontier packet's primary source plus this packet's changed files
(source/...) into <output>-source inside the repository, builds it with the frontier
packet's archived recipe (v1.44 SDK, workspace layout, physical-source wrapper,
optional verified external-only dependency cache), asserts the recorded ELF hashes,
then measures every original window with tools/measure.py and asserts the counts.

  python research/claude-pump-hi-20261027/reproduce.py --registry-home ~/.cargo \
      --output work/pump-hi-reproduce [--dependency-cache DIR]
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ROOT = next(p for p in P.parents if (p / 'evidence/original/pump/deployed.so').is_file())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--registry-home', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--dependency-cache', type=Path)
    a = ap.parse_args()
    rec = json.loads((P / 'RESULT.json').read_text())
    frontier = ROOT / rec['frontier_packet']
    out = a.output.resolve()
    src = out.with_name(out.name + '-source')
    assert not out.exists() and not src.exists(), 'output paths must not exist'
    shutil.copytree(frontier / 'primary', src)
    for rel, digest in rec['changed_files_sha256'].items():
        assert sha(P / 'source' / rel) == digest, rel
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(P / 'source' / rel, src / rel)
    sys.path.insert(0, str(frontier / 'inputs/scripts'))
    path = frontier / 'inputs/scripts/pump_build_verified.py'
    spec = importlib.util.spec_from_file_location('archived_pump_builder', path)
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    b.ROOT = ROOT
    sys.argv = [str(path), '--source-directory', str(src), '--workspace-layout',
                '--registry-home', str(a.registry_home.resolve()), '--output', str(out)]
    if a.dependency_cache:
        sys.argv += ['--dependency-cache', str(a.dependency_cache.resolve())]
    b.main()
    assert sha(out / 'candidate.so') == rec['candidate_sha256'], 'candidate hash differs'
    assert sha(out / 'unstripped.so') == rec['unstripped_sha256'], 'unstripped hash differs'
    measured = out / 'measure.json'
    subprocess.run([sys.executable, str(P / 'tools/measure.py'), '--packet', str(frontier),
                    '--candidate', str(out / 'unstripped.so'), '--output', str(measured)], check=True)
    m = json.loads(measured.read_text())
    assert m['counts'] == rec['counts'], (m['counts'], rec['counts'])
    assert not m['delta_vs_baseline']['normalized_losses'] and not m['delta_vs_baseline']['raw_losses']
    print('Reproduced both ELF hashes and the measured window counts:', json.dumps(rec['counts']))


if __name__ == '__main__':
    main()
