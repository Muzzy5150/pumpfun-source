#!/usr/bin/env python3
"""Stdlib-only check of the pump-mid Mayhem O0084 packet.

Checks the artifact hashes, then recomputes the window statuses of the shipped
symbols ELF against `evidence/original/mayhem/deployed.so`. It uses the repository's
stdlib-only `research/mayhem-provider-sharing/reader.py` normalizer and the
provider-sharing parent-audit window list. It also recomputes the shipped
sell_v2_handler body size. Every result must equal CLAIM.json.
"""
import gzip, hashlib, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = next(p for p in P.parents if (p / 'evidence/original/mayhem/deployed.so').is_file())
PKT = ROOT / 'research/mayhem-provider-sharing'
sha = lambda b: hashlib.sha256(b).hexdigest()


def main():
    claim = json.loads((P / 'CLAIM.json').read_text())
    sums = dict(reversed(line.split()) for line in (P / 'artifacts/SHA256SUMS').read_text().splitlines() if line.strip())
    cand = gzip.decompress((P / 'artifacts/candidate.so.gz').read_bytes())
    syms = gzip.decompress((P / 'artifacts/symbols.so.gz').read_bytes())
    assert sha(cand) == sums['candidate.so'] == claim['candidate_sha256'], 'stripped artifact hash'
    assert sha(syms) == sums['symbols.so'] == claim['symbols_sha256'], 'symbols artifact hash'
    assert sha((P / 'source.patch').read_bytes()) == claim['source_patch_sha256'], 'source.patch hash'
    spec = importlib.util.spec_from_file_location('provider_reader', PKT / 'reader.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    tmp = P / '.verify-symbols.so'
    tmp.write_bytes(syms)
    try:
        o = m.Elf((ROOT / 'evidence/original/mayhem/deployed.so').resolve()); c = m.Elf(tmp.resolve())
    finally:
        tmp.unlink()
    key = lambda w: (w['end'] - w['start'], w['normalized_sha256'], json.dumps(w['normalization_pattern'], sort_keys=True))
    rows = json.loads(gzip.decompress((PKT / 'inputs/parent-audit.json.gz').read_bytes()))['rows']
    cw = {a: c.window(a, z) for a, z in {(s['value'], s['value'] + s['size']) for s in c.symbols
                                          if s['info'] & 15 == 2 and s['size'] >= 8 and c.lo <= s['value'] < c.hi}}
    index = defaultdict(list)
    for w in cw.values():
        index[key(w)].append(w)
    matched = raw = 0; unmatched = []
    for r in rows:
        w = o.window(r['start'], r['end']); hits = index[key(w)]
        matched += bool(hits); raw += any(z['raw_sha256'] == w['raw_sha256'] for z in hits)
        if not hits:
            unmatched.append(r['id'])
    sell = [s for s in c.symbols if 'sell_v2_handler' in s['name'] and s['info'] & 15 == 2]
    sizes = sorted({s['size'] for s in sell})
    result = {'matched': matched, 'raw': raw, 'unmatched': sorted(unmatched), 'sell_v2_handler_bytes': sizes}
    for k in result:
        assert result[k] == claim[k], (k, result[k], claim[k])
    print(json.dumps({'verified': True, **result}))


if __name__ == '__main__':
    sys.exit(main())
