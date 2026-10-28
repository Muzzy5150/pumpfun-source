# Archive reproduction flow for the data-order option

This is a reasoning audit of the final implementation and existing build
evidence. It does not claim a new archive build was executed.

An old certificate is not a portable recipe. Its baseline receipts, ELF,
map, cache manifest and text recipe are absolute-path/hash bindings. The
primary-source comparison is canonicalized, but the evidence paths are not.
Moving or changing those inputs invalidates the old certificate. The R33
control also demonstrates that an R32 certificate rejects changed primary
source even when the intended two objects remain recognizable.

## Archive inputs

Preserve the primary, unstaged source tree (including its original
`Cargo.toml`, lockfile and known IDL/config inputs), the qualified SDK/profile
specification and tooling, and these separate files:

- **Pure text recipe**: copy the file named by
  `data-order-certificate.json → payload.text_order` as `text-order.ld`.
- **Combined recipe**: retain the final build's `ordered.ld` for evidence.
- The old certificate and data transformation report for provenance.
- Expected candidate/unstripped hashes and the ordinary build receipts.

The combined `ordered.ld` is not an admissible `--text-section-order` input
to a new derivation. Its data rule is already expanded. The deriver requires
the pure text recipe so it can generate the two-object data rule itself.
Do not edit the old JSON paths or remove its binding checks.

## Rebuild sequence

1. Verify the archive and use its primary source. Preserve the qualified
   native compiler/host files and hybrid SBF-library profile. Use the recorded
   registry/config context. A differing cache context needs a genuine new
   ordinary producer; do not relabel or substitute an old cache.
2. Make a fresh identity build from that primary source, with a fresh target
   and the existing identity-text recipe that emits an lld map. Retain the
   successful `build-attempt.json`, `build-comparison.json`, ELF and map.
3. Run the installed `pump_derive_data_order.py` with this **new identity
   build**, the archived **pure** `text-order.ld`, and a new certificate path.
   It rederives the two objects and current selectors, verifies their types
   and adjacency, and binds the current source/profile and new evidence.
4. Run a fresh verified build with the same source/profile/cache, that pure
   text recipe and the **new** `--data-order-certificate`. Only verified
   external dependencies may be reused; main is compiled again.
5. Require `data_order.status == passed`, the full-file transformation report,
   and exact equality of both final ELF hashes with the archive's expected
   hashes. A transformation pass alone proves preservation relative to the
   fresh identity build; it does not establish archive byte reproduction.
   Run the archive's required runtime/receipt checks before accepting it.

If a fresh identity build changes source hashes, cache/toolchain context,
object identity, selector names or linker-input bytes, the corresponding
gate must fail. Investigate and regenerate only from truthful current
inputs. If the archived pure text recipe no longer maps the same compiled
sections, do not silently declare a newly ordered result equal to the old
archive: final byte equality remains the acceptance condition.

## Evidence supporting this reasoning

- `FINAL-RESULT.json` records successful native default, hybrid text-only,
  and data-enabled builds with exact reference ELF equality.
- `R33-REBINDING-FINAL.json` shows rejection of a stale source certificate
  and acceptance after derivation from the newer identity build.
- `CONTROLS-V3.json` rejects stale baseline hashes, changed objects/selectors,
  compiler/profile drift and linker-input differences.
- `FINALIZATION-CONTROLS.json` proves failed final integrity checks do not
  leave a successful comparison report.

All five tracked TypeIds still differ from the original. This procedure
does not establish original toolchain provenance or whole-original-ELF
identity.
