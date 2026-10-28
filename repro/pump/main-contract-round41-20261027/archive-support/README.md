# Private data-order archive support

This packet verifies archived main-Pump artifacts without treating relocation of
an archive as fresh build admission. It does not change shared tools, source,
the admitted certificate, or the frozen data-order implementation. No compiler
was run in this lane.

## Read-only verifier

`verify_archive.py` exposes this keyword-only API:

```python
verify_archive(
    original_elf=..., baseline_elf=..., baseline_map=...,
    final_elf=..., final_map=..., admitted_certificate=...,
    bindings=..., bindings_sha256=..., tools_directory=...,
)
```

The CLI uses the same names with hyphens, plus `--output NEW_REPORT.json`.
`bindings_sha256` must come from the authenticated outer checkpoint manifest.
Do not compute it from a potentially changed bindings file and call that an
independent trust check. The bindings file contains schema1, exact SHA256/length
records for the six explicit artifact paths, and the admitted certificate's
11-file helper implementation closure. Paths are supplied independently, so
an archive may be relocated.

The verifier:

1. Checks all six artifact hashes/lengths, the fixed main-original hash and
   the sealed helper closure. The unchanged admitted certificate binds the
   archived baseline ELF/map hashes. Its old absolute paths are not followed.
2. Independently finds the unique original-normalized owner bodies for
   `0x101448/1640B` and `0x10c20/88B` in both explicit maps/ELFs, then checks their
   LDDW targets at offsets1616/56. Each target must own exactly one24/32-byte
   map input with alignment8.
3. Rechecks the Borsh Location `src/de/mod.rs:637:21`, the table's8/8 scalar
   layout, valid pointer relocations, and normalized drop/fmt methods against
   original `0xaef0/8B` and `0xa8f0/48B`. It verifies reversed adjacency before
   and corrected adjacency after, with identical input-section identities.
4. Uses temporary, hash-checked duplicate files to call the **unchanged**
   sealed `verify_transform`. Its small replay context is built from the
   independently observed roles. It is not a certificate: there is no call to
   `load_certificate`, `derive_payload`, or `check_request`, and no JSON path
   rewriting. A private temporary helper root also permits imports when the
   archive is outside the original checkout.
5. Rechecks inputs before returning. The CLI writes a report only on success.

The full transform accounts for all allocated and remaining file bytes, text
operands/branches/calls, data pointer/scalar fields, relocation sites/values and
both symbol tables. Other data movement, extra/missing input sections, changed
fields or unaccounted bytes fail. Python `-O` is rejected.

This replays artifact evidence. It does not re-run source, SDK, external-cache
or compiler admission. The outer archive source/build/profile manifest remains
authoritative. The concrete original Rust table type and allocation extents
remain unproved. TypeId equality is not checked by this utility; all five
tracked TypeIds still differ in the tested R32 artifact. Whole-original-ELF and
original-toolchain identity remain unproved.

## Fresh reproduction

`reproduction.py plan --request REQUEST.json --output PLAN.json` validates the
archived primary-file hashes and pure/identity recipes, then emits argv arrays;
it **does not execute** them. `REPRODUCTION-REQUEST.json` and
`REPRODUCTION-PLAN.json` show the tested R32 shape. Actual installation needs
the complete verified-builder repository/helper layout, archived inputs and
qualified hybrid profile. The plan binds all tool files it observes; their
hashes must also agree with the outer archive manifest.

Execute the plan sequentially only when a fresh reproduction is authorized:

1. Build a fresh identity ELF/map/standard receipts from archived primary with
   the identity text recipe, same explicit profile and correctly keyed external
   cache. Main is compiled again. If the cache context changes, establish an
   ordinary clean producer and parity proof; never relabel another cache.
2. Derive a **new** certificate from that identity build and archived pure
   `text-order.ld`. Do not reuse or edit the old admitted certificate.
3. Compile a fresh final with the pure text recipe and new certificate. Retain
   the generated combined `ordered.ld` separately; it is not a replacement
   pure input for later derivation.
4. Run `reproduction.py verify-final` with `--build`, `--certificate`, both
   `--candidate-sha256` and `--unstripped-sha256`, and a new `--output`.
   Both exact expected ELF hashes, successful standard before/after receipts,
   fresh-main flag, passed data-order status, and certificate/transformation
   hash bindings are required.
5. Replay the archive verifier with the **fresh** identity/final paths and
   fresh certificate, bound by a new outer manifest. Complete required runtime
   and signed-transaction receipt checks. Keep identity separate from final.

The plan and receipt gate were tested with existing R32 files only. No fresh
archive build or runtime was executed here. Prior text-only checkpoints retain
their existing verifier path; this support is selected only for data-enabled
artifacts.

## Evidence and controls

- `POSITIVE-FINAL.json`: current complete explicit-path replay proof.
- `CONTROLS.json`:19 archive checks, including two independent external-path
  replays, hash controls and deeply rebound corruption controls. Rebinding in a
  negative test deliberately tests structural defenses after the hash layer;
  it is not a permissible archival trust procedure.
- `CLI-CONTROLS.json`:positive CLI plus wrong-digest/missing-file rejection;
  failed calls leave no report.
- `REPRODUCTION-CONTROLS.json`:14 plan/final-receipt checks. The two final hashes
  are independently required; stale source/recipes, combined-as-pure script,
  reused output, stale certificates and incomplete receipts are rejected.
- `FIXTURE.json`:exact original source paths and copied archive paths. The
  original admitted certificate bytes are unchanged.
- `TEST-HISTORY.json`:the preserved first control-harness correction and
  superseded initial report. Use final reports for integration.
