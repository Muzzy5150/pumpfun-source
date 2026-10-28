"""Seal one fully validated main-Pump checkpoint; publication remains a separate step."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip, hashlib, json, shutil, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[2]
W = Path(__file__).resolve().parent
P = ROOT / 'repro/pump/main-contract-round21-20261027'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if data[:2] == b'\x1f\x8b' else data)
def run(command, log):
    with (W / log).open('w') as stream:
        subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
start = time.monotonic()
while True:
    state = read(W / 'round21-check-state.json')
    if state['status'] in ['passed', 'failed']:
        break
    if time.monotonic() - start > 1800:
        raise TimeoutError('Round21 validation did not finish')
    time.sleep(2)
assert state['status'] == 'passed', state
assert (ROOT/'work/parallel-main-round20-publication/PUSHED.json').is_file()
proof = read(ROOT/'work/parallel-main-create-sizing/DIRECT-TRAIT-PARITY.json')
current = read(W/'build-round21/build-comparison.json')
assert proof['status']=='passed'
assert proof['cache_key']==current['dependency_cache']['key']
assert proof['manifest_sha256']==current['dependency_cache']['manifest_sha256']
cached = W / 'build-round21'
clean = W / 'build-round21-repeat'
parity = {kind: {'cached': sha(cached / filename), 'repeat': sha(clean / filename)} for kind, filename in [('candidate','candidate.so'),('unstripped','unstripped.so')]}
assert all(len(set(row.values())) == 1 for row in parity.values())
(W / 'round21-cached-repeat-parity.json').write_text(json.dumps(parity, indent=2) + '\n')
subprocess.run([sys.executable,str(W/'check_call_closure.py'),'--inventory',str(W/'build-round21/normalized-inventory.json'),'--output',str(W/'round21-closed-call-body-inventory.json')],cwd=ROOT,check=True)
subprocess.run([sys.executable, str(W / 'promote_round21.py')], cwd=ROOT, check=True)
subprocess.run([sys.executable, str(W / 'package_round21.py')], cwd=ROOT, check=True)
registry = str(ROOT / 'work/parallel-main-create-sizing/build-direct-trait/cargo-home')
cache = str(ROOT / 'work/parallel-main-cache/direct-cache')
jobs = {
    'canonical': [sys.executable, str(ROOT/'scripts/pump_build_verified.py'), '--source-directory', str(ROOT/'programs/pump'), '--workspace-layout', '--registry-home', registry, '--dependency-cache', cache, '--output', str(W/'canonical-round21-build')],
    'archive': [sys.executable, str(P/'reproduce.py'), '--registry-home', registry, '--dependency-cache', cache, '--output', str(W/'archive-round21-build')],
}
with ThreadPoolExecutor(max_workers=2) as pool:
    for future in as_completed([pool.submit(run, command, f'round21-{name}-reproduction.log') for name, command in jobs.items()]):
        future.result()
builds = {'cached': cached, 'repeat': clean, 'canonical': W/'canonical-round21-build', 'archive': W/'archive-round21-build'}
four = {kind: {name: sha(folder/filename) for name,folder in builds.items()} for kind,filename in [('candidate','candidate.so'),('unstripped','unstripped.so')]}
assert all(len(set(row.values())) == 1 for row in four.values())
shutil.copy2(W/'canonical-round21-build/build-comparison.json', P/'canonical-build.json')
shutil.copy2(W/'archive-round21-build/build-comparison.json', P/'reproduced-build.json')
(P/'build-parity.json').write_text(json.dumps(four, indent=2) + '\n')
(W/'round21-four-build-parity.json').write_text(json.dumps(four, indent=2) + '\n')
cp = read(P/'CHECKPOINT.json')
cp['archived_recipe_reproduced'] = True
(P/'CHECKPOINT.json').write_text(json.dumps(cp, indent=2) + '\n')
subprocess.run([sys.executable, str(W/'write_round21_readme.py')], cwd=ROOT, check=True)
for name in ['REVIEW.json', 'benchmark.json']:
    source = ROOT/'work/parallel-main-loader-optimized'/name
    if source.is_file():
        target = P/'loader-optimization'/name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(source, target)
manifest = {str(path.relative_to(P)): sha(path) for path in sorted(P.rglob('*')) if path.is_file() and path.name != 'MANIFEST.json'}
(P/'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
run([sys.executable, str(P/'verify.py')], 'round21-public-verifier.log')
subprocess.run([sys.executable, str(W/'update_round21_queue.py')], cwd=ROOT, check=True)
result = {'status': 'verified', 'candidate_sha256': cp['candidate_sha256'], 'unstripped_sha256': cp['unstripped_sha256'], 'normalized_windows': cp['normalized_windows'], 'raw_windows': cp['raw_windows'], 'full_cases': cp['full_cases'], 'additional_cases': cp['additional_cases'], 'manifest_sha256': sha(P/'MANIFEST.json'), 'build_parity': four, 'goal_complete': False}
(W/'ROUND21-VERIFIED.json').write_text(json.dumps(result, indent=2) + '\n')
print(result, flush=True)
