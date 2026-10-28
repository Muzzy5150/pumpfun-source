# Verified-builder text-order option: private validation

The v2 patch was applied only to `scripts-v2/`; shared scripts and main source
remain unchanged. `run_builder_v2.py` loads that isolated builder and changes
only its repository-location constant so the normal workspace/source binding
can run inside this repository. It does not change compilation functions.

Four recommended builds completed with fresh main compilation and verified
external dependency cache key `fdf6441c…`:

| Build | Result |
|---|---|
| `r27-default02` | Both ELF hashes equal frozen default R27; option omitted. |
| `r27-ordered02` | Both ELF hashes equal the separately qualified R27 ordered artifact. |
| `r28-identity02` | Empty selector list preserves both frozen default R28 ELF hashes and records its map. |
| `r28-ordered02` | Newly derived R28 order; fresh compilation equals the bound relink. |

Each passes `verify_native_build_v2.py`, including the **actual**
`pump_tokenkeg_two_curve_differential.compiled_binding` check. The standard
completed `build-attempt.json` exists next to `build-comparison.json`, with
before/after source manifests equal. No compatibility adapter is needed.

Both R27 and R28 preserve **723 normalized windows** and increase raw windows
**123 → 135**, with no normalized/raw losses. R28's allocated-image translation
passes 940 sections, 10,714 direct calls and 5,812 relocation records. This does
not claim whole-ELF identity: unallocated symbol data and some section-header
fields are outside the checker. No runtime corpus was rerun by this lane.

R28 ordered outputs:

- Candidate: `6791b39c866bae8c1c3ceb6f1b9786e2ad2a8c7adfb7b7c75ce00c474569efd1`
- Unstripped: `2e2e5dbd8f72cc86c2801c911ab9844ee6582b8576ed1c251a419d171de19157`

`RESULT.json` records the four receipts, exact hashes, sets, and helper modes.
`../parallel-main-verified-linker-option-v2/PATCH-INPUTS.json` gives the five-file
patch hashes; `proposed-builder-option.patch` there is the final proposal.
The initial two optional builds failed before compilation because the v1
wrapper rejected Cargo's `rustc -vV` query. Their sources, attempts and logs are
retained. V2 forwards non-compilation queries and passes 19 offline controls.

## Integration recipe for changed main source

Wait for R28 publication before shared builder edits. Batch the validated source
changes first; do not reuse an earlier source's order. All output directories
below must be new. The example uses the isolated builder; after review and
installation, the equivalent public entry point is `scripts/pump_build_verified.py`.

1. Build the new source with `identity-order.ld`. It has no explicit selectors,
   so the original catch-all preserves default order while the linker records
   the actual map. If a normal verified build of this source exists, require
   both ELF hashes to equal it. A dependency/profile change requires a newly
   established ordinary external cache first; ordered cache misses are rejected.
2. Measure that default artifact and derive a qualified order from **its** map.
   The archived 1,035 original-window boundaries are fixed evidence, not code
   input. No original ELF bytes enter the compiler or linker.
3. Compile the same frozen source into another fresh target using the derived
   script. Measure complete normalized/raw sets, compare for losses, and run
   the allocated-image translation check.
4. Run the native receipt gate and then the full current corpus, diagnostics,
   captured-loader checks and signed-transaction retention gate. Pass the
   standard build receipt and its adjacent completed attempt; use no adapter.

Example commands (`NEW_SOURCE` and `NEW_OUT` are placeholders):

```sh
work/test-env/bin/python -B work/parallel-main-verified-linker-validation/run_builder_v2.py \
  --source-directory NEW_SOURCE --workspace-layout \
  --registry-home work/parallel-main-create-sizing/build-direct-trait/cargo-home \
  --dependency-cache work/parallel-main-cache/direct-cache \
  --text-section-order work/parallel-main-verified-linker-validation/identity-order.ld \
  --output NEW_OUT/default
work/test-env/bin/python -B work/parallel-main-verified-linker-validation/layout_tools/measure.py \
  --candidate NEW_OUT/default/unstripped.so \
  --windows-from work/parallel-main-integration/build-round28/normalized-inventory.json \
  --output NEW_OUT/default-inventory.json.gz
work/test-env/bin/python -B work/parallel-main-verified-linker-validation/layout_tools/derive_layout.py \
  --windows-from NEW_OUT/default-inventory.json.gz \
  --candidate NEW_OUT/default/unstripped.so --map NEW_OUT/default/link/link.map \
  --output-dir NEW_OUT/order
work/test-env/bin/python -B work/parallel-main-verified-linker-validation/run_builder_v2.py \
  --source-directory NEW_SOURCE --workspace-layout \
  --registry-home work/parallel-main-create-sizing/build-direct-trait/cargo-home \
  --dependency-cache work/parallel-main-cache/direct-cache \
  --text-section-order NEW_OUT/order/ordered.ld --output NEW_OUT/ordered
work/test-env/bin/python -B work/parallel-main-verified-linker-validation/layout_tools/translation.py \
  --baseline NEW_OUT/default/unstripped.so --baseline-map NEW_OUT/default/link/link.map \
  --reordered NEW_OUT/ordered/unstripped.so --reordered-map NEW_OUT/ordered/link/link.map \
  --output NEW_OUT/translation.json
work/test-env/bin/python -B work/parallel-main-verified-linker-validation/verify_native_build_v2.py \
  --build NEW_OUT/ordered
```

The layout tools are unchanged copies of the reviewed tools. Exact hashes and
all retained inputs are in `MANIFEST.json`; compiled targets and registry
symlinks are excluded. The individually copied link inputs remain included.
