#!/usr/bin/env python3
"""Independently re-measure every shipped amm-mid candidate.

For each gains/*/candidate (and gains/*/history-*/candidate) directory:
  * decompress the stripped and unstripped ELFs into a temporary directory,
  * check them against the recorded SHA-256 values,
  * run the repository measurement tool
    (repro/pump_amm/focused-diagnostics-20261026/measure.py) on them,
  * compare the counts with the recorded claim and with the shipped measure JSON,
  * re-measure the named frontier candidate and report gained/lost windows.
Finally, check that source.patch applied to the current frontier canonical source
reproduces the shipped full files under source/.
No compiler or VM is executed. Exit status is non-zero on any discrepancy.
"""
import gzip, hashlib, json, subprocess, sys, tempfile
from pathlib import Path

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
MEASURE = ROOT / 'repro/pump_amm/focused-diagnostics-20261026/measure.py'
CANONICAL = ROOT / 'repro/pump_amm/account-context-recovery-20261027/results/canonical-source'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def measure(candidate, symbols, out):
    subprocess.run([sys.executable, '-B', str(MEASURE), '--candidate', str(candidate), '--symbols', str(symbols),
                    '--output', str(out)], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    return json.loads(out.read_text())


def matched(m):
    return {r['start'] for r in m['rows'] if r['matches']}, {r['start'] for r in m['rows'] if r['raw_match']}


def main():
    failures = []
    frontier_cache = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for i, cand_dir in enumerate(sorted(PACKET.glob('gains/**/candidate'))):
            claim = json.loads((cand_dir / 'sha256.json').read_text())
            work = tmp / f'c{i}'; work.mkdir()
            stripped = work / 'pump_amm_recovered.so'; unstripped = work / 'unstripped.so'
            stripped.write_bytes(gzip.decompress((cand_dir / 'pump_amm_recovered.so.gz').read_bytes()))
            unstripped.write_bytes(gzip.decompress((cand_dir / 'unstripped.so.gz').read_bytes()))
            ok = sha(stripped.read_bytes()) == claim['candidate_sha256'] and sha(unstripped.read_bytes()) == claim['unstripped_sha256']
            m = measure(stripped, unstripped, work / 'measure.json')
            counts = {k: m[k] for k in ('windows', 'normalized_matches', 'raw_matches', 'unmatched')}
            ok &= all(claim['measurement'][k] == v for k, v in counts.items())
            shipped = cand_dir.parent / 'measurement.json.gz'
            if shipped.exists():
                ok &= json.loads(gzip.decompress(shipped.read_bytes()))['rows'] == m['rows']
            fpath = ROOT / claim['frontier'] / 'results/build'
            if claim['frontier'] not in frontier_cache:
                fm = measure(fpath / 'candidate.so', fpath / 'unstripped.so', work / 'frontier.json')
                assert sha((fpath / 'candidate.so').read_bytes()) == claim['frontier_candidate_sha256']
                frontier_cache[claim['frontier']] = fm
            fn, fr = matched(frontier_cache[claim['frontier']]); cn, cr = matched(m)
            report = {'candidate': str(cand_dir.relative_to(PACKET)), 'sha256_ok': ok, **counts,
                      'frontier': claim['frontier'], 'gained': [hex(x) for x in sorted(cn - fn)],
                      'lost': [hex(x) for x in sorted(fn - cn)], 'raw_gained': [hex(x) for x in sorted(cr - fr)],
                      'raw_lost': [hex(x) for x in sorted(fr - cr)]}
            print(json.dumps(report))
            if not ok or report['lost'] or report['raw_lost']:
                failures.append(report['candidate'])
        # source.patch reproduces shipped files from the current frontier canonical source
        work = tmp / 'src'
        subprocess.run(['cp', '-R', str(CANONICAL / 'programs'), str(work)], check=True)
        subprocess.run(['patch', '-s', '-p2', '-d', str(work), '-i', str(PACKET / 'source.patch')], check=True)
        for f in sorted((PACKET / 'source/programs').rglob('*.rs')):
            rel = f.relative_to(PACKET / 'source/programs')
            same = (work / rel).read_bytes() == f.read_bytes()
            print(json.dumps({'source_file': str(rel), 'patch_reproduces_shipped_file': same}))
            if not same:
                failures.append(str(rel))
    if failures:
        sys.exit('FAILED: ' + ', '.join(failures))
    print('OK')


if __name__ == '__main__':
    main()
