# Mayhem O0084 SellV2: price-check order, signer-seed order and IR-proven residual causes

Lane `pump-mid` (continued by lane `mayhem-o84`), on the Mayhem **434** parent: `claude-mayhem-work/mayhem-env/parent-434` (cp4 + O0073; stripped `e0d0d0c3…`, symbols `828751f9…`). The first steps were measured on parent-433 (cp4, stripped `c1f25d01…`, symbols `73c28d5e…`); `source.patch` applies unchanged to both.
Target: O0084 `sell_v2_handler` (original `0x26db8` / 159,160, 18,096 bytes).

**No window is gained** and nothing is lost:
- 434/441 normalized (on parent-434) and 100 raw-local are preserved;
- positive direct-call edges and Source records are unchanged (`measure/`);
- there are no `Stack offset` warnings.

The packet ships one behaviour-neutral source change that moves O0084 measurably closer to the original. It also records IR-level proofs of the remaining causes.

| SellV2 body | Bytes | Masked ratio | Differing masked lines |
| --- | ---: | ---: | ---: |
| Original | 18,096 | 1 | 0 |
| 433 parent | 17,960 | 0.7887 | 906 |
| 433 + v01 (price before scaled) | 17,888 | 0.8687 | 544 |
| 433/434 + v14 | 17,896 | 0.8853 | 469 |
| 434 + w23 (CPI `Result` bound in a block) | 17,912 | 0.8872 | 468 |
| **434 + `source.patch` (x02: v14 + signer seeds inline after the account struct)** | **17,944** | **0.9312** | **280** |

"Masked" means the `r10` frame offsets, registers, call and lddw immediates and branch displacements are all masked (`tools/irx.py`). It is a progress gauge only; matching is decided by the repository normalizer in `measure/`.

## Source change (`source.patch`, git-applyable from the parent-434 root)

**Signer seeds (x02, lane mayhem-o84).** The original reads `ctx.bumps.sol_vault` after the 26 `AccountInfo` clones, right before the account struct is copied into the `CpiContext` (original offset 10,016). The patch therefore drops the named `bump`/`seeds` locals (the line is left empty) and passes `&[&[b"sol-vault",&[ctx.bumps.sol_vault]]]` inline as `new_with_signer`'s third argument. This closes the whole 10,000–11,000 account-array copy region (468 → 280 lines). The CPI keeps v14's `if sell_v2(…).is_ok() {…} else {…}` form; see PROGRESS.md for the other forms.

The price-check part has three changes, made in the closure. Line count and every Source record are preserved; the 7 O0084 Source records equal the original's.

1. Compute `price` (the `checked_div`) before the scaled multiply. This is v01, described next.
2. `let delta = match reference.checked_mul(tolerance_bps as u128) { Some(scaled) => scaled / 10_000, None => return Err(MathOverflow) };`
3. `let high = match reference.checked_add(delta) { Some(high) => high, None => return Err(MathOverflow) };`

The explicit `match` with work in the Some arm keeps core's `unlikely` weights on both overflow edges. That reproduces the llc target `n1` (469 lines).

v01 detail:

`price` (the `checked_div` by `virtual_token_reserves`) is computed before `scaled` (the `checked_mul` by `tolerance_bps`).
- Both failures return `MathOverflow` and neither computation has side effects, so behaviour is unchanged.
- The 14 trade suites pass: **6,636 cases, 0 mismatches, 0 non-compute log differences**.
- The rebuilt function equals the `llc` output of the parent IR with `umul.with.overflow` sunk below the `vt == 0` branch (IR experiment `i1`).
- The original therefore tests `virtual_token_reserves == 0` before multiplying `reference * tolerance`.

## Post-CPI result drop (w23)

The original builds the `PumpCpiFailed` AnchorError first and drops the CPI's `Err` payload afterwards. Ours (`if sell_v2(…).is_ok()`) dropped the `Result` at the end of the `if` condition, before building the error.

**w23 fixes this** by binding the `Result` inside a block that ends right after the error is built: `{ let outcome = sell_v2(…); if outcome.is_ok() { Ok(()) } else { Err(error!(..)) } }`.
- The call's `&[seeds]` temporary still dies at the end of the call statement, so the CPI account-info construction keeps v14's code.
- The post-CPI region now has the original shape: `mov r7, r0; mov r6, r1`, then the error built, then the drop.

**Diagnosis behind it.** The w14 and w17 IR differ only in block order: the error-construction block moves directly after the call. The construction-region code is identical in IR, so the machine-code changes there are register allocation following block order.
- Every form that extends the `&[seeds]` temporary's lifetime (`match` / `if let` / `map_err` on the call, w17–w19) or names the signer (w20–w22) perturbs it.
- With MIR JumpThreading off (diagnosis only), v14 scores 564 and w20 scores 666, so the original was built with JumpThreading behaving as ours does.

The packet shipped the w23 build on **parent-434**: 434/441, 100 raw-local, no losses, 0 `Stack offset` warnings, 7/7 Source records equal to the original. `source.patch` applies unchanged to parent-433 and parent-434.

## IR-level findings (llc from the same v1.54 toolchain; `ir/exps*.py`)

The rustc-emitted IR, compiled with `llc -O3 -mtriple=sbf -mcpu=generic -relocation-model=pic -function-sections`, reproduces the built `sell_v2_handler` exactly.

1. **Zero check before the scaled multiply (`i1`).** Closed by `source.patch` (906 → 544 lines).
2. **Branch weights decide the price-check layout (`n1`: 544 → 469 lines). Closed in source by v14.**
   - The original's block order is reproduced when the `checked_mul` (scaled) and `checked_add` (high) overflow edges carry `unlikely` weights, while the `checked_sub` (low) and slippage-comparison edges carry none.
   - The 2-valued error trampoline then moves to the function end (`jne r8, 0, @17768` as in the original), and the error-construction block sits inline after the low check.
   - That is exactly core's hint pattern: `checked_mul`, `checked_add` and `checked_div` use `intrinsics::unlikely`; unsigned `checked_sub` does not.
   - In our build only `checked_div`'s hint survives. A per-pass trace of the closure (`-print-after-all`) shows that LowerExpectIntrinsic attaches `!prof` to all three branches.
   - SimplifyCFG then folds the empty `checked_mul` and `checked_add` Option diamonds, because the product or sum is computed before the branch, and their weights are lost.
   - `checked_div` keeps its weight because its Some arm contains the `udiv`.
   - **Source forms that do keep both hints:** `match` with the division in the `checked_mul` Some arm (v10, 537 lines), plus `match` on `checked_add` (v12 and v14, 470 and 469 lines).
     - v12 deleted a line and shifted two SellV2 Source records (591:25 and 592:26 became 590 and 591). v14 keeps the line count, and its Source records equal the original's.
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
| 256–1430 | Price-check layout is now the original's. What remains is the `vs` load placement (finding 3; v13 = v14 plus an inline read scores 530) and register reloads of `reference.lo` |
| 1890–3710 | Cap selection and the inlined `sell_amounts`. In the original, the `retained_reserve_bps > 10000` check and the raw `vs * balance / (vt + balance)` come first, and the default/WSOL cap selection comes after the raw quote. In our IR the selection (`%.sink` 104/184) precedes `sell_amounts`. Likely fix: select the cap inside `sell_amounts` after the raw output, which changes a helper shared with Legacy Sell, so coordinate with pump-lo. The original loads the quote-mint key words and the global-params base (`+8`, then `96`/`176`) before the default/WSOL comparisons; ours compares first and folds the offsets to `104`/`184`. `sell_amounts` is in `state.rs`, shared with Legacy Sell (pump-lo); it is **not** modified here. |
| 4736, 10016–10872 | CPI construction: **closed by x02** (signer seeds evaluated after the account struct) |
| 14384–14832 | Post-CPI: the original keeps the CPI `Result` in r7/r6, builds `PumpCpiFailed`, then drops the `Err` payload; x02 drops it first (14 lines). Forms that move the drop rescheduled the clone region (PROGRESS.md) |
| 14120–16700 | Event and record-sell tail: block order of error and `unwrap_failed` paths |

## Reproduce

```sh
# parent: cp -R claude-mayhem-work/mayhem-env/parent-434 ROOT && chmod -R u+w ROOT && git -C ROOT apply research/claude-pump-mid-mayhem-o0084/source.patch
python3 claude-mayhem-work/sbf_lock.py --slots 6 --name sbf -- \
  python3 claude-mayhem-work/mayhem-b/build/build_lane.py o84-x02e ROOT o84-a
python3 -B claude-mayhem-work/mayhem-b/build/measure.py mayhem-b/out/builds/o84-x02e/symbols.so <434 symbols.so>
REPO/work/test-env/bin/python -B claude-mayhem-work/mayhem-b/build/run_trades.py <worktree> candidate.so OUTDIR 3
HOME=$(mktemp -d) python3 -B research/claude-pump-mid-mayhem-o0084/verify.py
```

`verify.py` uses only the standard library and the repository's `research/mayhem-provider-sharing/reader.py`. It checks the artifact hashes and the patch hash.
It recomputes 434 normalized and 100 raw-local windows from `artifacts/symbols.so.gz`, the 7 unmatched windows, and the 17,944-byte SellV2 body, and compares all of them with `CLAIM.json`.
The 14 per-suite outputs (61 MB) are kept out of the packet; `runtime/suite-output-SHA256SUMS` binds them.
`tools/irx.py` (IR surgery and scoring) and `tools/var.py` (parallel source variants) are the lane tools; `tools/o84/` holds the continuation lane's copies (race-free `var.py`, `pack.py` packet refresher, `regions.py`/`hunks.py`/`dis.py` diff views, `fx.py`/`irnorm.py` IR extraction and normalization); `ir/` holds every experiment spec (`ir/o84-s*.json` for the continuation).
