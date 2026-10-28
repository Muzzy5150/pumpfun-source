# Main Pump indirect-call audit

All **144 original `CALL_REG` sites** are catalogued with raw operand evidence and register provenance:

- **63** use the tagged `std::io::Error` custom-object pattern, loading the boxed error vtable and its drop slot. The shape agrees with the pinned SDK's bitpacked error representation. The concrete heap vtable remains unresolved.
- **81** are formatter/value/trait dispatches. Exact normalized candidate bodies supply display labels; those labels are not treated as authenticated original names or target proof.
- No site has an input-independent constant target in the conservative local analysis. **61** retain an input-dependent symbolic load chain; **83** widen to unknown across calls, joins, or unsupported operations. Widening is an analysis limit, not proof that the target is arbitrary.

Two sites have a verified fixed target in known direct-call contexts: **`0x1ae098` and `0x1ae230`**, inside the inferred `0x1adfb0` formatter body. All **30 known direct calls** to that body come from `0xc680` and load argument register `r3` with **`0x1bd8a0`**. The method at table offset **24** is a loader-relocated pointer to **`0xa880`**. Original instruction bytes independently check all 30 argument loads, yielding **60 fixed caller/site edges**. The existing Round24 data-frontier report independently maps the same table reference; its 64-byte prefix is not used as proof of a whole object.

This is **conditional static resolution**, not a global target-set proof. No relocated function pointer to `0x1adfb0` was found, but an unmodelled computed/indirect entry could still pass another vtable. All 144 unrestricted target sets therefore remain unproved. No new function boundary, program source, or published table was changed; no target program was executed.

Files:

- `SITES.tsv`: compact 144-site catalogue.
- `CLASSIFICATION.json`: raw evidence, labels, status, input hashes, and limitations.
- `LOCAL-PROVENANCE.json`: symbolic register results and one-hop direct-call contexts.
- `RESOLVED-CONTEXTS.json`: the 60 conditional fixed-target edges and byte-check proof.

Reproduce with Python's standard library:

```sh
python3 -B work/parallel-main-indirect-call-audit/trace.py --output work/parallel-main-indirect-call-audit/LOCAL-PROVENANCE.json
python3 -B work/parallel-main-indirect-call-audit/classify.py --output work/parallel-main-indirect-call-audit/CLASSIFICATION.json
```

The analysis retains both conditional successors, caps abstract value sets, forgets caller-clobbered registers and modeled stack memory after calls, and reads constant pointers only from the original read-only program data. Numeric targets use linked original text addresses before the VM base relocation.
