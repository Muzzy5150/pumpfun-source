# Bounded immutable-data comparison

The Round24 frontier's 64-byte previews were replaced with field-by-field comparisons over supported value footprints. No preview is treated as a complete object.

| Value family | Typed-role support | Footprint | Result |
| --- | ---: | --- | --- |
| Location-compatible payload | 82 | 24 bytes | 46 field-equal after pointer relocation; 36 differ in file/line/column |
| Debug vtable | 13 | 32 bytes | Size/alignment and both function-pointer fields correspond |
| Write vtable | 1 | 48 bytes | Size/alignment and four function-pointer fields correspond |
| Format pieces slice | 11 | Explicit count × 16 bytes | All 27 string slices and 389 referenced string bytes agree |

The vtables contain **30 compared function-pointer fields**, targeting 25 distinct original windows. Each pointer is decoded from its actual relocation and checked against the corresponding candidate target's complete normalized body. This does not prove transitive code/data identity.

A further **18 location-shaped pairs** have no accepted typed-call transport and remain shape hypotheses. Their 24-byte previews are retained separately. **240 other `.data.rel.ro` reference pairs** remain unclassified. The frontier also contains 613 `.rodata` and 24 `.text` reference pairs; this packet does not assign them object identities.

Evidence for the footprints:

- Location fields follow the selected 64-bit core layout: a 16-byte string slice plus two 32-bit coordinates. Typed register transport is checked against original call instructions and the matching candidate call sites, with pinned `track_caller` signatures. The forwarding stub at `0x1b0580` is treated through its original next-entry slice-index failure target, not through an ambiguous eight-byte candidate symbol.
- Vtable consumers identify Debug or Write trait arguments. The selected layout has a three-word drop/size/alignment header and one or three method slots, respectively. Scalar fields, relocation kinds, and each function target are compared individually.
- Format pieces obtain their array length from caller-written `fmt::Arguments` slice fields before `panic_fmt`. Each string pointer and explicit byte length is then followed within the ELF's file-backed sections.

These are **bounded typed-value comparisons**, not proof of original allocation extents, authenticated historical Rust type names, or whole-data identity. Original allocations could include padding or participate in merged constants. All records retain `allocation_extent_proved: false`; function target comparison remains local. No program source, ELF, or public inventory was edited.

Reproduce with Python's standard library:

```sh
python3 -B work/parallel-main-data-layout-proof/audit.py --output work/parallel-main-data-layout-proof/AUDIT.json --summary work/parallel-main-data-layout-proof/SUMMARY.json
```

`AUDIT.json` records each field, relocation, call-site proof, input hash, and uncertainty. `VALUES.tsv` is the compact inventory. A second run produced byte-identical audit and summary outputs; see `REPRODUCTION-CHECK.json`.
