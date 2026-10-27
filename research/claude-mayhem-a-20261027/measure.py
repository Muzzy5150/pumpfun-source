#!/usr/bin/env python3
"""Re-measure candidate ELFs against the 441 original Mayhem windows (no rebuild).

Uses the unchanged normalizer of research/mayhem-trade-origins-validator/reader.py
and the window list of its audit.json (the same 441 windows every Mayhem packet
uses).  A window is matched when some candidate FUNC symbol range has the same
size, normalized SHA-256 and normalization pattern; raw_local when the raw bytes
are also equal.  This is the rule of the parent packets' analysis.py.

usage: measure.py [--repository-root R] SYMBOLS.so[.gz] [--base BASE_SYMBOLS.so[.gz]] [--json OUT]
"""
import argparse, collections, gzip, hashlib, importlib.util, json, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(root):
    pkt = root / 'research/mayhem-trade-origins-validator'
    spec = importlib.util.spec_from_file_location('mayhem_reader', pkt / 'reader.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows = [(r['id'], r['start'], r['end']) for r in json.loads((pkt / 'audit.json').read_text())['rows']]
    assert len(rows) == 441
    return mod, rows


def elf(mod, path, td):
    path = Path(path)
    data = path.read_bytes()
    if path.suffix == '.gz':
        data = gzip.decompress(data)
    tmp = Path(td) / (hashlib.sha256(data).hexdigest() + '.so')
    tmp.write_bytes(data)
    return mod.Elf(tmp), hashlib.sha256(data).hexdigest()


def sig(w):
    return (w['end'] - w['start'], w['normalized_sha256'], json.dumps(w['normalization_pattern'], sort_keys=True))


def measure(mod, rows, original, path, td):
    C, digest = elf(mod, path, td)
    groups = set()
    for f in C.symbols:
        if f['info'] & 15 == 2 and f['size'] >= 8 and C.lo <= f['value'] < C.hi:
            groups.add((f['value'], f['value'] + f['size']))
    cw = {k: C.window(*k) for k in groups}
    bysig = collections.defaultdict(list)
    for k, w in cw.items():
        bysig[sig(w)].append(k)
    status = {}
    for wid, a, b in rows:
        w = original[wid]
        hits = bysig.get(sig(w), [])
        raw = any(cw[k]['raw_sha256'] == w['raw_sha256'] for k in hits)
        status[wid] = 'raw_local_match' if raw else 'normalized_only' if hits else 'unmatched'
    return status, digest, C.hi - C.lo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('symbols')
    ap.add_argument('--base')
    ap.add_argument('--json')
    ap.add_argument('--repository-root', type=Path, default=HERE.parents[1])
    a = ap.parse_args()
    root = a.repository_root.resolve()
    mod, rows = load(root)
    O = mod.Elf(root / 'evidence/original/mayhem/deployed.so')
    assert hashlib.sha256(O.b).hexdigest() == 'a87fa9f866272514e6acb852b668c4a08aeb173d56c883039991d114d1199bdb'
    original = {wid: O.window(s, e) for wid, s, e in rows}
    size = {wid: e - s for wid, s, e in rows}
    out = {}
    with tempfile.TemporaryDirectory() as td:
        for label, path in [('candidate', a.symbols)] + ([('base', a.base)] if a.base else []):
            st, digest, text = measure(mod, rows, original, path, td)
            c = collections.Counter(st.values())
            unm = sorted(k for k, v in st.items() if v == 'unmatched')
            out[label] = dict(symbols_sha256=digest, text_bytes=text, normalized=c['raw_local_match'] + c['normalized_only'],
                              raw_local=c['raw_local_match'], unmatched=unm, unmatched_bytes=sum(size[k] for k in unm), status=st)
            print(f"{label}: {Path(path).name} sha256={digest[:16]}… normalized={out[label]['normalized']}/441 "
                  f"raw_local={out[label]['raw_local']} unmatched={len(unm)} ({out[label]['unmatched_bytes']} B)")
    if a.base:
        s, b = out['candidate']['status'], out['base']['status']
        out['delta'] = dict(
            normalized_gains=sorted(k for k in s if b[k] == 'unmatched' and s[k] != 'unmatched'),
            normalized_losses=sorted(k for k in s if b[k] != 'unmatched' and s[k] == 'unmatched'),
            raw_gains=sorted(k for k in s if b[k] != 'raw_local_match' and s[k] == 'raw_local_match'),
            raw_losses=sorted(k for k in s if b[k] == 'raw_local_match' and s[k] != 'raw_local_match'))
        for k, v in out['delta'].items():
            print(f'{k}: {len(v)} {" ".join(v)}')
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
