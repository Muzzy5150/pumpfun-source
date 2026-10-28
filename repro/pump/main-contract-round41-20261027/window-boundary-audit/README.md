# Main Pump inferred-window audit

No missing, overlapping, or contradicted boundary was found in the checked static evidence. The **1,035 ranges remain inferred windows**, not authenticated historical Rust function extents.

- The windows cover all **1,792,208 bytes** of `.text` (`0x120..0x1b59f0`) exactly, with no gap, overlap, misalignment, or boundary in a wide instruction. The sole executable `PT_LOAD` is exactly this range.
- All **10,591 relative calls** (905 distinct targets), the one defined-symbol call relocation (`custom_panic`), **279 relocated code pointers** (137 distinct targets), the ELF entrypoint, and both `STT_FUNC` starts are represented. No relative call or branch targets an invalid instruction; no branch crosses a window boundary. No unrelocated `lddw` points into `.text`.
- All 1,035 starts have one of those evidence sources. The fixed table exactly reproduces the historical ledger; the reviewed producer hashes agree with its published manifest.
- Both original symbol sizes (`entrypoint`: 440 bytes; `custom_panic`: 200 bytes) agree with their window ends. All 152 windows ending in `CALL` have a callee inferred not to return by the conservative CFG analysis; no reachable fallthrough across a boundary remains. That analysis uses `abort` as its sole external non-return seed and is conditional on the recorded partition.

The unresolved limit is **144 indirect call sites**. Their full dynamic targets were not established. Relocated code pointers provide entry evidence, but do not prove unique source functions, names, or historical end positions. An unreferenced function or a computed target could remain within a larger window. This audit therefore supports the current denominator for the stated static evidence; it does not prove an exact historical function count or whole-ELF identity.

`inventory_current.py` reads the fixed TSV and compares local bodies; it is not a boundary-discovery or completeness verifier. No production source, ELF, or published table was changed.

Reproduce with Python's standard library:

```sh
python3 work/parallel-main-window-boundary-audit/audit.py --output work/parallel-main-window-boundary-audit/AUDIT.json --summary work/parallel-main-window-boundary-audit/SUMMARY.json
```

The complete call/pointer/boundary ledger is in `AUDIT.json`; `SUMMARY.json` contains counts and input hashes; `SOURCE-REVIEW.json` records the producer/matcher review.

Input SHA-256:

- Original ELF: `7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d`
- Fixed table: `fb2c0a47514567d65eb45c1e268dacd5291e4659bb7dceb575a767dc20bcaff8`
- Audit script: `a9764f20f039de2e75660de14d9a224da718ed99654869af1691a821ac2bcc00`
