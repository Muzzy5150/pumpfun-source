"""Verify ordinary new-graph producer/consumer parity and native source receipts."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    directories = [HERE / name for name in ['plain-producer01', 'plain-consumer01', 'ordered-consumer01']]
    records = [json.loads((d / 'build-comparison.json').read_text()) for d in directories]
    spec = importlib.util.spec_from_file_location('entrypoint_native_gate', ROOT / 'scripts/pump_tokenkeg_two_curve_differential.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    bindings = []
    source_sets = []
    for directory, record in zip(directories, records):
        assert record['returncode'] == 0 and record['source_unchanged']
        attempt = json.loads((directory / 'build-attempt.json').read_text())
        assert attempt['returncode'] == 0 and attempt['source_unchanged']
        assert attempt['source_sha256'] == attempt['source_after_sha256'] == record['source_sha256']
        gate.SOURCE_DIRECTORY = Path(record['source_directory'])
        bindings.append(gate.compiled_binding(directory / 'candidate.so', directory / 'build-comparison.json'))
        workspace = Path(record['source_directory']).parents[1]
        source_sets.append({str((ROOT / k).relative_to(workspace)): v for k, v in record['source_sha256'].items()})
        assert record['dependency_cache']['main_freshly_compiled']
    assert source_sets[0] == source_sets[1] == source_sets[2]
    producer, consumer, ordered = records
    assert 'text_layout' not in producer and 'text_layout' not in consumer
    assert producer['environment']['RUSTC_WRAPPER'] == str(ROOT / 'scripts/pump_physical_source_wrapper.py')
    assert producer['dependency_cache']['status'] == 'miss'
    assert producer['dependency_cache']['external_fresh'] == 0
    assert consumer['dependency_cache']['status'] == ordered['dependency_cache']['status'] == 'hit'
    cache_key = producer['dependency_cache']['key']
    assert cache_key != 'fdf6441ce812bf7050ae2af8ca0708104ae04c5dedd4b610613364f964b41e29'
    assert {x['dependency_cache']['key'] for x in records} == {cache_key}
    manifest = Path(producer['dependency_cache']['cache_root']) / cache_key / 'MANIFEST.json'
    manifest_hash = sha(manifest)
    assert {x['dependency_cache']['manifest_sha256'] for x in records} == {manifest_hash}
    cache = json.loads(manifest.read_text())
    assert cache['producer_build_report'] == str(directories[0] / 'build-comparison.json')
    assert 'text_layout' not in cache['producer_build_report_snapshot']
    assert not any('pump_recovered' in path or 'pump-recovered' in path for path in cache['files'])
    hashes = {}
    for file in ['candidate.so', 'unstripped.so']:
        hashes[file] = {'clean': sha(directories[0] / file), 'cached': sha(directories[1] / file)}
        assert hashes[file]['clean'] == hashes[file]['cached'] == sha(HERE / 'clean-default01' / file)
        assert sha(directories[2] / file) == sha(HERE / 'relink-ordered01' / file)
    lock = HERE / 'source/Cargo.lock'
    result = {'status': 'passed', 'clean_build': str(directories[0]), 'cached_build': str(directories[1]),
              'clean_build_directory': str(directories[0]), 'cached_build_directory': str(directories[1]),
              'elf_hashes': hashes, 'cache_key': cache_key,
              'cache_root': producer['dependency_cache']['cache_root'],
              'registry_home': producer['environment']['CARGO_HOME'],
              'manifest_sha256': manifest_hash,
              'clean_build_report_sha256': sha(directories[0] / 'build-comparison.json'),
              'cached_build_report_sha256': sha(directories[1] / 'build-comparison.json'),
              'fresh_main': True, 'primary_lockfile': str(lock), 'primary_lockfile_sha256': sha(lock),
              'producer_kind': 'ordinary physical-wrapper clean build; no ordered recipe or imported artifacts',
              'producer_target_unavailable_control': json.loads((HERE / 'PRODUCER-INDEPENDENCE.json').read_text()),
              'ordered_consumer': str(directories[2]),
              'ordered_consumer_candidate_sha256': sha(directories[2] / 'candidate.so'),
              'ordered_consumer_unstripped_sha256': sha(directories[2] / 'unstripped.so'),
              'ordered_matches_bound_relink': True, 'native_bindings': bindings}
    (HERE / 'DIRECT-TRAIT-PARITY.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'cache_key', 'manifest_sha256', 'elf_hashes', 'ordered_matches_bound_relink']}, indent=2))


if __name__ == '__main__':
    main()
