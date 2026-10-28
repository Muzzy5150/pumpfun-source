#!/usr/bin/env python3
"""Replace the Token-2022 TLV helpers with the original's slice-walking form.

  python3 -B tools/apply_tlv.py --source-directory <crate> [--only len|quote] [--variant DIR]

  len   -> src/migrate_v2.rs required_quote_account_len  (window 0x17c0f0)
  quote -> src/create_v2.rs  quote_extensions_supported  (window 0x17bc48)

Each body in tools/tlv/[<variant>/]<name>.rs replaces one top-level function, from its
`pub fn` line (plus the attribute lines the body itself starts with) to the first column-0
`}`. The replacement keeps the file's line count, so no Source coordinate elsewhere in
create_v2.rs or migrate_v2.rs moves. Content-addressed: re-running is a no-op.
"""
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGETS = {'len': ('src/migrate_v2.rs', 'required_quote_account_len'),
           'quote': ('src/create_v2.rs', 'quote_extensions_supported')}


def replace_fn(path, name, body):
    lines = path.read_text().split('\n')
    new = body.rstrip('\n').split('\n')
    k = next(i for i, l in enumerate(new) if l.startswith(f'pub fn {name}('))  # attribute lines in the body
    starts = [i for i, l in enumerate(lines) if l.startswith(f'pub fn {name}(')]
    assert len(starts) == 1, (path, name, starts)
    s = starts[0]
    e = next(i for i in range(s, len(lines)) if lines[i] == '}')
    if s >= k and lines[s - k:e + 1] == new:
        return 'already'
    # the frontier text has no attribute of its own above `pub fn` when the body brings one
    lo = s - k if k and all(lines[s - k + j] == new[j] for j in range(k)) else s
    assert len(new) == e + 1 - lo, f'{name}: {len(new)} lines replace {e + 1 - lo}'
    lines[lo:e + 1] = new
    path.write_text('\n'.join(lines))
    return 'applied'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--source-directory', type=Path, required=True)
    ap.add_argument('--only', choices=sorted(TARGETS))
    ap.add_argument('--variant', default='')
    a = ap.parse_args()
    for key, (rel, name) in TARGETS.items():
        if a.only and a.only != key:
            continue
        body = HERE / 'tlv' / a.variant / f'{name}.rs'
        if not body.exists():
            print(name, 'no body in', body.parent)
            continue
        print(name, replace_fn(a.source_directory / rel, name, body.read_text()))


if __name__ == '__main__':
    main()
