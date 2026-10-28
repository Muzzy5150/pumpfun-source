from pathlib import Path
import hashlib
import json
import shutil

root = Path(__file__).resolve().parents[2]
work = Path(__file__).resolve().parent
before = work / 'source01'
after = work / 'source02'
assert not after.exists()
shutil.copytree(before, after)
path = after / 'src/create_v2.rs'
source = path.read_text()
gate = ' require_eq!(a.global.create_v2_enabled,true,PumpError::CreateV2Disabled);\n'
creator = ' require_keys_neq!(creator,Pubkey::default(),PumpError::CreatorShouldNotBeZero);\n'
assert source.count(gate) == source.count(creator) == 1
source = source.replace(gate, '').replace(creator, creator + gate)
path.write_text(source)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def hashes(directory):
    return {str(p.relative_to(directory)): sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}

a, b = hashes(before), hashes(after)
assert list(k for k in a if a[k] != b[k]) == ['src/create_v2.rs']
report = {
    'baseline': str(before), 'source': str(after),
    'baseline_files': a, 'source_files': b,
    'change': 'Move CreateV2Disabled comparison after cashback, holder-reward selection and nonzero-creator validation, retaining source01 Mayhem enable and quote policy corrections.',
    'before_result': {'path': str(work / 'early-pairs-before.json.gz'), 'sha256': sha(work / 'early-pairs-before.json.gz'), 'cases': 12, 'mismatches': 6},
}
(work / 'PLAN02.json').write_text(json.dumps(report, indent=2) + '\n')
manifest = json.loads((work / 'manifest.json').read_text())
manifest.append({'name': 'create_early_pairs', 'script': 'work/parallel-main-create-gate-order/probe_early_pairs.py', 'count': 12})
(work / 'manifest02.json').write_text(json.dumps(manifest, indent=2) + '\n')
(work / 'focused-manifest02.json').write_text(json.dumps(manifest[-4:], indent=2) + '\n')
print(sha(path))
print('cases', sum(x['count'] for x in manifest))
