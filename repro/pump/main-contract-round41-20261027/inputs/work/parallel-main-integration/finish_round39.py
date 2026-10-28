"""Package R36 after root promotion; never mutate the maintained source.

Uses existing round39-build-config fields only: registry_home, dependency_cache,
sdk, target_library_profile, target_library_directory and the existing cache
proof fields consumed by package_round39.py. Root must provide a passed
round39-check-state.json, completed initial/repeat data builds, the initial
identity build, round39-layout/{ordered.ld,text-order.ld,data-order-certificate.json},
round39-promotion.json, and the three-script approval/hash gate before execution.
The archive reproducer creates its separate identity and certificate siblings;
this finisher binds their receipts only after both final ELF hashes agree.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip, hashlib, json, shutil, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[2]
W = Path(__file__).resolve().parent
P = ROOT / 'repro/pump/main-contract-round39-20261027'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if data[:2] == b'\x1f\x8b' else data)
def run(command, log):
    with (W / log).open('w') as stream:
        subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
# Root writes this gate only after reviewing the final packaging scripts.
approval = W / 'ROUND39-PACKAGING-APPROVED.json'
approval_start = time.monotonic()
while not approval.is_file():
    if time.monotonic() - approval_start > 7200:
        raise TimeoutError('Round39 packaging approval did not arrive')
    time.sleep(2)
approved = read(approval)
assert approved['status'] == 'approved', approved
for name in ['package_round39.py', 'finish_round39.py', 'write_round39_readme.py']:
    assert sha(W / name) == approved['scripts_sha256'][name], ('Unreviewed packaging script', name)
start = time.monotonic()
while True:
    try:
        state = read(W / 'round39-check-state.json')
    except OSError as exc:
        if exc.errno not in (23,24):raise
        time.sleep(2);continue
    if state['status'] in ['passed', 'failed']:
        break
    if time.monotonic() - start > 1800:
        raise TimeoutError('Round39 validation did not finish')
    time.sleep(2)
assert state['status'] == 'passed', state
assert (ROOT/'work/parallel-main-round38-publication/PUSHED.json').is_file()
frozen_corpus=W/'unified-main-corpus-round39.json'
frozen_corpus_sha256=sha(frozen_corpus)
corpus=read(frozen_corpus)
assert set(corpus['counts'])=={'full','additional'}
for group,total in corpus['counts'].items():
 rows=[r for r in corpus['suites']if r['group']==group]
 assert rows and len({r['name']for r in rows})==len(rows) and sum(r['cases']for r in rows)==total
 report=read(W/('round39-captured-full.json.gz'if group=='full'else'round39-captured-additional.json.gz'))
 assert report['case_count']==total and report['suite_count']==len(rows)
 assert set(report['suites'])=={r['name']for r in rows},'Missing or extra frozen suites'
assert sha(frozen_corpus)==frozen_corpus_sha256
CFG=read(W/'round39-build-config.json')
proof = read(Path(CFG['cache_proof']))
current = read(W/'build-round39/build-comparison.json')
assert proof['status']=='passed'
assert CFG['target_library_profile']=='linux-v1.44-sbf'
assert current['target_library_profile']['cache_context']==proof['profile_context']
assert current['target_library_profile']['native_host_files_unchanged'] is True
assert proof['cache_key']==current['dependency_cache']['key']
assert proof['manifest_sha256']==current['dependency_cache']['manifest_sha256']
cached = W / 'build-round39'
clean = W / 'build-round39-repeat'
parity = {kind: {'cached': sha(cached / filename), 'repeat': sha(clean / filename)} for kind, filename in [('candidate','candidate.so'),('unstripped','unstripped.so')]}
assert all(len(set(row.values())) == 1 for row in parity.values())
(W / 'round39-cached-repeat-parity.json').write_text(json.dumps(parity, indent=2) + '\n')
subprocess.run([sys.executable,str(W/'check_call_closure.py'),'--inventory',str(W/'build-round39/normalized-inventory.json'),'--output',str(W/'round39-closed-call-body-inventory.json')],cwd=ROOT,check=True)
# Root owns promotion; packaging verifies its completed receipt and source.
assert (W/'round39-promotion.json').is_file(),'Root must promote the verified source before packaging'
sys.path.insert(0,str(ROOT/'scripts'))
from build_source_manifest import source_manifest
current_primary={str((Path(k) if Path(k).is_absolute() else ROOT/k).relative_to(ROOT/'programs/pump')):v for k,v in source_manifest(ROOT/'programs/pump',ROOT/'programs/pump',ROOT).items()}
primary=Path(current['primary_source_directory'])
expected_primary={str((Path(k) if Path(k).is_absolute() else ROOT/k).relative_to(primary)):v for k,v in current['primary_source_sha256'].items()}
assert current_primary==expected_primary,'Maintained source differs from approved build'
assert read(W/'round39-promotion.json')['candidate_sha256']==current['comparison']['candidate_sha256']
if P.exists():
    preserved=W/'round39-initial-package-incomplete'
    assert not (P/'MANIFEST.json').is_file(),'Do not overwrite a sealed checkpoint'
    assert not preserved.exists()
    P.rename(preserved)
subprocess.run([sys.executable,str(ROOT/'work/parallel-main-data-frontier/audit_source_paths.py'),'--before',str(ROOT/'repro/pump/main-contract-round38-20261027/full.json.gz'),'--after',str(W/'round39-captured-full.json.gz'),'--output',str(ROOT/'work/parallel-main-data-frontier/round39-source-path-fidelity.json')],cwd=ROOT,check=True)
subprocess.run([sys.executable, str(W / 'package_round39.py')], cwd=ROOT, check=True)
registry = CFG['registry_home']
cache = CFG['dependency_cache']
jobs = {
    'canonical': [sys.executable, str(ROOT/'scripts/pump_build_verified.py'), '--source-directory', str(ROOT/'programs/pump'), '--workspace-layout', '--registry-home', registry, '--dependency-cache', cache, '--text-section-order', str(W/'round39-layout/ordered.ld'), '--data-order-certificate',str(W/'round39-layout/data-order-certificate.json'), '--target-library-profile',CFG['target_library_profile'],'--target-library-directory',CFG['target_library_directory'],'--sdk',CFG['sdk'],'--output', str(W/'canonical-round39-build')],
    'archive': [sys.executable, str(P/'reproduce.py'), '--registry-home', registry, '--dependency-cache', cache, '--target-library-directory',CFG['target_library_directory'],'--sdk',CFG['sdk'],'--output', str(W/'archive-round39-build')],
}
with ThreadPoolExecutor(max_workers=2) as pool:
    for future in as_completed([pool.submit(run, command, f'round39-{name}-reproduction.log') for name, command in jobs.items()]):
        future.result()
builds = {'cached': cached, 'repeat': clean, 'canonical': W/'canonical-round39-build', 'archive': W/'archive-round39-build'}
four = {kind: {name: sha(folder/filename) for name,folder in builds.items()} for kind,filename in [('candidate','candidate.so'),('unstripped','unstripped.so')]}
assert all(len(set(row.values())) == 1 for row in four.values())
shutil.copy2(W/'canonical-round39-build/build-comparison.json', P/'canonical-build.json')
shutil.copy2(W/'archive-round39-build/build-comparison.json', P/'reproduced-build.json')
(P/'build-parity.json').write_text(json.dumps(four, indent=2) + '\n')
(W/'round39-four-build-parity.json').write_text(json.dumps(four, indent=2) + '\n')
cp = read(P/'CHECKPOINT.json')
assert cp['frozen_corpus_sha256']==frozen_corpus_sha256==sha(frozen_corpus)
for group,total in corpus['counts'].items():
 assert cp[group+'_cases']==total and cp[group+'_suites']==sum(r['group']==group for r in corpus['suites'])
for label,folder in builds.items():
 record=read(folder/'build-comparison.json');profile=record['target_library_profile']
 assert profile['status']=='verified' and profile['native_host_files_unchanged'] is True
 assert profile['cache_context']==cp['target_library_profile_context']
 manifest_file=folder/'target-library-profile-files.json'
 assert sha(manifest_file)==profile['file_manifest_sha256']
 destination=P/cp['target_library_profile_manifests'][{'cached':'build.json','repeat':'repeat-build.json','canonical':'canonical-build.json','archive':'reproduced-build.json'}[label]]
 destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(manifest_file,destination)
# Preserve the fresh archived identity and certificate without rewriting either.
archive_result=read(W/'archive-round39-build/archive-reproduction.json')
assert archive_result['status']=='passed' and archive_result['fresh_certificate'] is True
archive_identity=Path(archive_result['identity_build_directory']);archive_certificate=Path(archive_result['certificate'])
assert archive_identity!=W/'build-round39-identity' and archive_identity!=W/'archive-round39-build'
assert sha(archive_certificate)==archive_result['certificate_sha256']
def archive_copy(src,dst):
    dst=P/dst;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
for source,destination in [('candidate.so','identity-candidate.so'),('unstripped.so','identity.so'),('link/link.map','identity.map'),('build-comparison.json','identity-build.json'),('build-attempt.json','identity-attempt.json'),('target-library-profile-files.json','identity-target-library-profile-files.json')]:
    archive_copy(archive_identity/source,Path('archive-reproduction')/destination)
archive_copy(archive_certificate,'archive-reproduction/certificate.json')
archive_copy(W/'archive-round39-build/archive-reproduction.json','archive-reproduction/receipt.json')
for record_name,directory,label,certificate_name in [('canonical-build.json',W/'canonical-round39-build','canonical','data-order/admitted-certificate.json'),('reproduced-build.json',W/'archive-round39-build','reproduced','archive-reproduction/certificate.json')]:
    record=read(directory/'build-comparison.json');transformation='data-order/'+label+'-transformation.json'
    assert record['data_order']['status']=='passed'
    assert record['data_order']['certificate_sha256']==sha(P/certificate_name)
    assert record['data_order']['transformation_sha256']==sha(directory/'data-order-transformation.json')
    archive_copy(directory/'data-order-transformation.json',transformation)
    archive_copy(directory/'link/link.map','data-order/'+label+'-final.map')
    cp['data_order']['builds'][record_name]={'certificate':certificate_name,'certificate_sha256':sha(P/certificate_name),'transformation':transformation,'transformation_sha256':sha(P/transformation)}
import importlib.util
spec=importlib.util.spec_from_file_location('finish_data_archive',P/'archive-support/verify_archive.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
cert=read(P/'archive-reproduction/certificate.json')
artifacts={'original_elf':ROOT/'evidence/original/pump/deployed.so','baseline_elf':P/'archive-reproduction/identity.so','baseline_map':P/'archive-reproduction/identity.map','final_elf':P/'unstripped.so','final_map':P/'data-order/reproduced-final.map','admitted_certificate':P/'archive-reproduction/certificate.json'}
bindings={'schema':1,'artifacts':{name:{'sha256':sha(path),'bytes':path.stat().st_size}for name,path in artifacts.items()},'tools':cert['payload']['implementation']}
(P/'archive-reproduction/bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
proof=module.verify_archive(**artifacts,bindings=P/'archive-reproduction/bindings.json',bindings_sha256=sha(P/'archive-reproduction/bindings.json'),tools_directory=P/'inputs/scripts')
(P/'archive-reproduction/proof.json').write_text(json.dumps(proof,indent=2)+'\n')
cp['data_order']['archive_replays']['reproduced']={'baseline_elf':'archive-reproduction/identity.so','baseline_map':'archive-reproduction/identity.map','final_map':'data-order/reproduced-final.map','certificate':'archive-reproduction/certificate.json','certificate_sha256':sha(P/'archive-reproduction/certificate.json'),'bindings':'archive-reproduction/bindings.json','bindings_sha256':sha(P/'archive-reproduction/bindings.json'),'proof':'archive-reproduction/proof.json'}
assert cp['data_order']['archive_replays']['initial']['certificate_sha256']!=cp['data_order']['archive_replays']['reproduced']['certificate_sha256']
cp['archive_identity_freshly_compiled']=True

cp['archived_recipe_reproduced'] = True
(P/'CHECKPOINT.json').write_text(json.dumps(cp, indent=2) + '\n')
subprocess.run([sys.executable, str(W/'write_round39_readme.py')], cwd=ROOT, check=True)
for name in ['REVIEW.json', 'benchmark.json']:
    source = ROOT/'work/parallel-main-loader-optimized'/name
    if source.is_file():
        target = P/'loader-optimization'/name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(source, target)
manifest = {str(path.relative_to(P)): sha(path) for path in sorted(P.rglob('*')) if path.is_file() and path != P/'MANIFEST.json'}
(P/'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
run([sys.executable, str(P/'verify.py')], 'round39-public-verifier.log')
subprocess.run([sys.executable, str(W/'update_round39_queue.py')], cwd=ROOT, check=True)
result = {'status': 'verified', 'candidate_sha256': cp['candidate_sha256'], 'unstripped_sha256': cp['unstripped_sha256'], 'normalized_windows': cp['normalized_windows'], 'raw_windows': cp['raw_windows'], 'full_cases': cp['full_cases'], 'additional_cases': cp['additional_cases'], 'manifest_sha256': sha(P/'MANIFEST.json'), 'build_parity': four, 'goal_complete': False}
(W/'ROUND39-VERIFIED.json').write_text(json.dumps(result, indent=2) + '\n')
print(result, flush=True)
