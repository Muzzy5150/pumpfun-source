# Remaining main-Pump data reference pairs

This read-only audit covers all 240 `.data.rel.ro` pairs left unclassified by `../parallel-main-data-layout-proof/AUDIT.json`, against the frozen Round24 ELF. It does not establish historical object or Rust type identity.

The candidate ELF supplies a `STT_OBJECT` start and unique size for each of the 240 references. Those are candidate allocation facts. The original is stripped, so the corresponding reads use candidate-sized comparison footprints; no original allocation extent is claimed.

The footprints contain:

- 38 trait-vtable-shaped records: four Error, four Write, one Any, and 29 other single-method trait tables. The four Error records all reference the same candidate `StringError` concrete type, through four separately emitted method copies. The fifth differing TypeId belongs to the Any table used by `panic_fmt`, consistent with the selected core `PanicInfo::internal_constructor::NoPayload`.
- Four records compatible with `std::io::SimpleMessage`; their message, length and ErrorKind integer agree.
- 198 string-slice tables, containing 234 slice elements. All element lengths and bytes agree. Two zero-length slices have the same nonrelocated dangling pointer value 1; they are not treated as relocated string objects. Sixteen of these arrays have direct format-argument pointer/count transport evidence at 50 observed calls. The other 182 remain layout-only classifications.

Of 108 compared vtable function-pointer fields, 103 target bodies match under the existing normalized inventory. Five 56-byte TypeId return bodies differ only in their two returned constants. The four nested Display-supertrait tables contribute another eight matching pointer fields. These are local body comparisons, not transitive byte identity.

The six original direct calls to `io::Error::_new` at `0x1a9db0` each pass one of the four Error-table constants. Their saved argument provenance is complete for these six direct calls. It does not close all heap origins or all indirect call targets.

`AUDIT.json` preserves every comparison, candidate symbol extent, source reference and input hash. `SUMMARY.json` is the compact view. See the separate `../parallel-main-typeid-provenance` packet for concrete candidate type binding and compiler/sysroot controls.

Reproduce with:

```sh
work/test-env/bin/python -B work/parallel-main-data-layout-remaining/audit.py \
  --output /tmp/pump-remaining-data-audit.json \
  --summary /tmp/pump-remaining-data-summary.json
```

No main source, original ELF, boundary table or normalized-match table is changed.
