#!/usr/bin/env python3
"""Round36+ main-Pump recipe for an arbitrary in-repo crate directory, step for step as the packet's
reproduce.py: identity build (identity .text order) -> fresh data-order certificate -> final build
(pure .text order + certificate), Linux v1.44 SBF target-library profile, verified dependency cache."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, sys
sys.dont_write_bytecode = True
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--packet', required=True, help='repo-relative frontier packet, e.g. repro/pump/main-contract-round36-20261027')
    ap.add_argument('--source-directory', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--dependency-cache', type=Path, required=True)
    ap.add_argument('--target-library-directory', type=Path, required=True)
    ap.add_argument('--registry-home', type=Path, default=Path.home() / '.cargo')
    ap.add_argument('--prepare-cache', action='store_true', help='first run one ordinary (unordered) build to populate the external dependency cache')
    a = ap.parse_args()
    ROOT = a.root.resolve(); P = ROOT / a.packet; cp = json.loads((P / 'CHECKPOINT.json').read_text())
    final = a.output.resolve(); identity = final.with_name(final.name + '-identity'); certificate = final.with_name(final.name + '-data-order-certificate.json')
    assert not final.exists() and not identity.exists() and not certificate.exists(), 'use fresh paths'
    pure = P / cp['text_section_order']; identity_script = P / cp['identity_text_order']
    assert sha(pure) == cp['text_section_order_sha256'] and sha(identity_script) == cp['identity_text_order_sha256']
    sys.path.insert(0, str(P / 'inputs/scripts'))
    path = P / 'inputs/scripts/pump_build_verified.py'
    spec = importlib.util.spec_from_file_location('archived_pump_builder', path); builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder); builder.ROOT = ROOT
    common = [str(path), '--source-directory', str(a.source_directory.resolve()), '--workspace-layout', '--registry-home', str(a.registry_home.resolve()),
              '--dependency-cache', str(a.dependency_cache.resolve()), '--target-library-profile', cp['target_library_profile'],
              '--target-library-directory', str(a.target_library_directory.resolve())]
    if a.prepare_cache:
        ordinary = final.with_name(final.name + '-ordinary'); assert not ordinary.exists()
        sys.argv = common + ['--output', str(ordinary)]; builder.main()
    sys.argv = common + ['--text-section-order', str(identity_script), '--output', str(identity)]; builder.main()
    first = json.loads((identity / 'build-comparison.json').read_text())
    assert first['returncode'] == 0 and first['source_unchanged']
    import pump_data_order
    sys.argv = [str(P / 'inputs/scripts/pump_derive_data_order.py'), '--baseline-build', str(identity), '--text-section-order', str(pure), '--output', str(certificate)]
    pump_data_order.main()
    sys.argv = common + ['--text-section-order', str(pure), '--data-order-certificate', str(certificate), '--output', str(final)]; builder.main()
    report = json.loads((final / 'build-comparison.json').read_text())
    assert report['returncode'] == 0 and report['source_unchanged'] and report['data_order']['status'] == 'passed'
    out = {'identity_unstripped_sha256': sha(identity / 'unstripped.so'), 'certificate_sha256': sha(certificate),
           'candidate_sha256': sha(final / 'candidate.so'), 'unstripped_sha256': sha(final / 'unstripped.so')}
    (final / 'r36-recipe.json').write_text(json.dumps(out, indent=2) + '\n'); print(json.dumps(out, indent=2))
if __name__ == '__main__': main()
