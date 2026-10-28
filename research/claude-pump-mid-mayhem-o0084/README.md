# Mayhem O0084 SellV2: price-check order and IR-proven residual causes

Lane `pump-mid`, on the Mayhem **433** parent: `claude-mayhem-work/mayhem-env/parent-433`, cp4 (stripped `c1f25d01…`, symbols `73c28d5e…`).
Target: O0084 `sell_v2_handler` (original `0x26db8` / 159,160, 18,096 bytes).

**No window is gained** and nothing is lost:
- 433/441 normalized and 100 raw-local are preserved;
- positive direct-call edges and Source records are unchanged (`measure/`);
- there are no `Stack offset` warnings.

The packet ships one behaviour-neutral source change that moves O0084 measurably closer to the original. It also records IR-level proofs of the remaining causes.

| SellV2 body | Bytes | Masked ratio | Differing masked lines |
| --- | ---: | ---: | ---: |
| Original | 18,096 | 1 | 0 |
| 433 parent | 17,960 | 0.7887 | 906 |
| 433 + `source.patch` | 17,888 | 0.8687 | 544 |

"Masked" means the `r10` frame offsets, registers, call and lddw immediates and branch displacements are all masked (`tools/irx.py`). It is a progress gauge only; matching is decided by the repository normalizer in `measure/`.

## Source change (`source.patch`, git-applyable from the parent-433 root)

In the price-check closure, `price` (the `checked_div` by `virtual_token_reserves`) is now computed before `scaled` (the `checked_mul` by `tolerance_bps`).
- Both failures return `MathOverflow` and neither computation has side effects, so behaviour is unchanged.
- The 14 trade suites pass: **6,636 cases, 0 mismatches, 0 non-compute log differences**.
- The rebuilt function equals the `llc` output of the parent IR with `umul.with.overflow` sunk below the `vt == 0` branch (IR experiment `i1`).
- The original therefore tests `virtual_token_reserves == 0` before multiplying `reference * tolerance`.

## IR-level findings (llc from the same v1.54 toolchain; `ir/exps*.py`)

The rustc-emitted IR, compiled with `llc -O3 -mtriple=sbf -mcpu=generic -relocation-model=pic -function-sections`, reproduces the built `sell_v2_handler` exactly.

1. **Zero check before the scaled multiply (`i1`).** Closed by `source.patch` (906 → 544 lines).
2. **Branch weights decide the price-check layout (`n1`: 544 → 469 lines).**
   - The original's block order is reproduced when the `checked_mul` (scaled) and `checked_add` (high) overflow edges carry `unlikely` weights, while the `checked_sub` (low) and slippage-comparison edges carry none.
   - The 2-valued error trampoline then moves to the function end (`jne r8, 0, @17768` as in the original), and the error-construction block sits inline after the low check.
   - That is exactly core's hint pattern: `checked_mul`, `checked_add` and `checked_div` use `intrinsics::unlikely`; unsigned `checked_sub` does not.
   - In our build only `checked_div`'s hint survives. A per-pass trace of the closure (`-print-after-all`) shows that LowerExpectIntrinsic attaches `!prof` to all three branches.
   - SimplifyCFG then folds the empty `checked_mul` and `checked_add` Option diamonds, because the product or sum is computed before the branch, and their weights are lost.
   - `checked_div` keeps its weight because its Some arm contains the `udiv`.
   - Source forms that do **not** keep the hint (all built and measured, no losses):
     - immediate `.ok_or(..)?` (v04);
     - `let … else` (v05);
     - `match` (v06);
     - no closure (v07: worse, 606 lines);
     - closure ending in `if/else` (v08).
3. **`virtual_sol_reserves` is loaded late (`j1`, `j2`).** The original loads it after the scaled `__multi3`s, inside the non-zero branch, and spills it for the later `sell_amounts` use.
   - Moving the load in IR fixes this region but costs elsewhere (544 → 593 lines), so it must be combined with the later-region fixes.
   - The source form (v03: reading the field inside the price expression) reproduces exactly that IR.

## Residual diagnosis (433 + patch, masked hunks larger than 2 lines)

| Original offsets | Diagnosis |
| --- | --- |
| 256–1430 | Price-check layout: branch weights (finding 2) and `vs` load placement (finding 3) |
| 1890–3710 | Cap selection and the inlined `sell_amounts`. The original loads the quote-mint key words and the global-params base (`+8`, then `96`/`176`) before the default/WSOL comparisons; ours compares first and folds the offsets to `104`/`184`. `sell_amounts` is in `state.rs`, shared with Legacy Sell (pump-lo); it is **not** modified here. |
| 4736, 10016–10872 | CPI construction and post-CPI reload/accounting blocks (31–39-line insertions and deletions) |
| 14120–16700 | Event and record-sell tail: block order of error and `unwrap_failed` paths |

## Reproduce

```sh
# parent: cp -R claude-mayhem-work/mayhem-env/parent-433 ROOT && git -C ROOT apply research/claude-pump-mid-mayhem-o0084/source.patch
python3 claude-mayhem-work/sbf_lock.py --slots 6 --name sbf -- \
  python3 claude-mayhem-work/mayhem-b/build/build_lane.py pm-o84-v01 ROOT pm-o84
python3 -B claude-mayhem-work/mayhem-b/build/measure.py mayhem-b/out/builds/pm-o84-v01/symbols.so <433 symbols.so>
REPO/work/test-env/bin/python -B claude-mayhem-work/mayhem-b/build/run_trades.py <worktree> candidate.so OUTDIR 3
HOME=$(mktemp -d) python3 -B research/claude-pump-mid-mayhem-o0084/verify.py
```

`verify.py` uses only the standard library and the repository's `research/mayhem-provider-sharing/reader.py`. It checks the artifact hashes and the patch hash.
It recomputes 433 normalized and 100 raw-local windows from `artifacts/symbols.so.gz`, the 8 unmatched windows, and the 17,888-byte SellV2 body, and compares all of them with `CLAIM.json`.
The 14 per-suite outputs (61 MB) are kept out of the packet; `runtime/suite-output-SHA256SUMS` binds them.
`tools/irx.py` (IR surgery and scoring) and `tools/var.py` (parallel source variants) are the lane tools; `ir/` holds every experiment spec.
