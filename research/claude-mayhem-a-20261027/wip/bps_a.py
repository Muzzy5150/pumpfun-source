from pathlib import Path
PAIRS = [["\n\npub fn bought_amounts(before_quote:u64", "\n#[inline(always)]\npub fn bought_amounts(before_quote:u64"]]
def edit(root):
    p = root / 'src/instructions/pump_amm_interface.rs'
    s = p.read_text()
    for old, new in PAIRS:
        assert s.count(old) == 1, (old, s.count(old))
        s = s.replace(old, new)
    p.write_text(s)
