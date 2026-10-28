#!/usr/bin/env python3
"""Preserve changed-domain behavior and compare all retained error values."""
import argparse
import concurrent.futures
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITES = {
    'authority': 'pump_validate_authority.py',
    'configuration': 'pump_validate_config_admin.py',
    'creator_distribution': 'pump_creator_distribution_differential.py',
    'minimum_distribution': 'pump_minimum_fee_differential.py',
    'admin_cto': 'pump_admin_cto_differential.py',
    'set_params': 'pump_set_params_differential.py',
    'set_creator': 'pump_set_creator_differential.py',
    'legacy_create': 'pump_create_differential.py',
    'create_v2': 'pump_create_quote_differential.py',
    'create_control': 'pump_create_control_differential.py',
    'holder_distribution': 'pump_holder_distribution_differential.py',
    'nested_create': 'pump_create_nested_differential.py',
    'legacy_sell': 'pump_legacy_sell_differential.py',
    'migration': 'pump_migrate_differential.py',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def error_messages(value):
    logs = []
    for key, v in value.items():
        if 'log' in key.lower() and isinstance(v, list):
            logs.extend(x for x in v if isinstance(x, str))
    result = {'anchor': [], 'panic': [], 'compared': []}
    pending = None
    for line in logs:
        if line.startswith('Program log: Left:') or line.startswith('Program log: Right:'):
            side, val = line.removeprefix('Program log: ').split(':', 1)
            if val.strip():
                result['compared'].append([side, val.strip()])
                pending = None
            else:
                pending = side
        elif pending is not None and line.startswith('Program log: '):
            result['compared'].append([pending, line.removeprefix('Program log: ')])
            pending = None
        else:
            pending = None
        if 'panicked at ' in line:
            result['panic'].append(line.split('\n', 1)[-1])
        if 'AnchorError' in line:
            found = re.search(r'Error Code: (.*?)\. Error Number: (\d+)\. Error Message: (.*)', line)
            result['anchor'].append(list(found.groups()) if found else line)
    return result, bool(logs)


def diagnostics(value, path=''):
    rows, covered = [], 0
    if isinstance(value, dict):
        if isinstance(value.get('original'), dict) and isinstance(value.get('candidate'), dict):
            a, al = error_messages(value['original'])
            b, bl = error_messages(value['candidate'])
            if al or bl:
                covered += 1
                if a != b:
                    rows.append({'path': path, 'case': value.get('case'), 'original': a, 'candidate': b})
        for key, v in value.items():
            if key not in ('original', 'candidate'):
                extra, count = diagnostics(v, path + '/' + key)
                rows.extend(extra)
                covered += count
    elif isinstance(value, list):
        for i, v in enumerate(value):
            extra, count = diagnostics(v, path + '/' + str(i))
            rows.extend(extra)
            covered += count
    return rows, covered


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--suites', nargs='*')
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    selected = a.suites or list(SUITES)
    candidate = a.candidate.resolve()
    candidate_sha = sha(candidate)

    def run(name):
        script = ROOT / 'scripts' / SUITES[name]
        before = sha(script)
        out = a.output / (name + '.json')
        with (a.output / (name + '.log')).open('w') as log:
            result = subprocess.run([sys.executable, str(script), '--candidate', str(candidate), '--output', str(out)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        assert before == sha(script) and candidate_sha == sha(candidate)
        raw = out.read_bytes()
        data = json.loads(gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw)
        bad, covered = diagnostics(data)
        summary = {'returncode': result.returncode, 'script_sha256': before, 'receipt_sha256': sha(out), 'diagnostic_coverage': covered, 'diagnostic_mismatches': bad, 'case_count': data.get('case_count', len(data.get('cases', [])))}
        print(name, 'returncode', result.returncode, 'diagnostic mismatches', len(bad), flush=True)
        return name, summary

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as workers:
        results = dict(workers.map(run, selected))
    summary = {'scope': 'Changed-domain published regression suites, including exact Anchor names/numbers/messages and all retained Left/Right values. Natural source coordinates and compute units remain excluded.', 'candidate_sha256': candidate_sha, 'original_sha256': sha(ROOT / 'evidence/original/pump/deployed.so'), 'suites': results}
    (a.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return any(r['returncode'] or r['diagnostic_mismatches'] for r in results.values())


if __name__ == '__main__':
    raise SystemExit(main())
