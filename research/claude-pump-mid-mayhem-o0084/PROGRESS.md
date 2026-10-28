# pump-mid / Mayhem O0084 SellV2: progress

## Setup (2026-10-27 ~21:50)

- Base: `claude-mayhem-work/mayhem-env/parent-433`, copied to `claude-mayhem-work/pm-o84/root`.
  - Rebuild reproduces stripped `c1f25d01…` and symbols `73c28d5e…`, with 0 `Stack offset` warnings.
  - Builds use `mayhem-b/build/build_lane.py` labels `pm-o84-*` under `claude-mayhem-work/sbf_lock.py`.
- O0084 on 433: 17,960 B against the original 18,096; masked ratio 0.7887, 906 differing masked lines.

## Results

| Step | O0084 bytes | Masked lines | Windows | Losses |
| --- | ---: | ---: | --- | --- |
| 433 parent | 17,960 | 906 | 433 / 100 raw | — |
| v01: price before scaled | 17,888 | 544 | 433 / 100 raw | none |
| **v14: v01 + `match` forms keeping core's `unlikely` hints (`source.patch`)** | **17,896** | **469** | 433 / 100 raw | none |

- Trade suites for v01 and v14: each 14 suites, 6,636 cases, 0 mismatches, 0 non-compute log differences.
- v14's 7 O0084 Source records equal the original's.
- v12 (same code minus one line) shifted two records, so it was rejected in favour of v14.
- The change is disjoint from O0073's `fee_recipients.rs` edit, so composing with PR #397 is a file-level union.
- **Shared helpers:** `state.rs` (`sell_amounts`, shared with Legacy Sell / pump-lo) is NOT changed. Only `pump_interface_v2.rs` (`sell_v2_handler`) changes.

## Experiments (all no-loss; masked lines on O0084)

IR (`ir/exps*.py`, llc on rustc IR):

| Experiment | Change | Lines |
| --- | --- | ---: |
| i1 / i2 | umul after the `vt == 0` check | 544 (= v01) |
| j1 / j2 | `vs` load late | 593 |
| k1 | scaled overflow unlikely | 536 |
| k2 | all edges unlikely | 568 |
| k3 | vt branch without weight | 585 |
| m1 | low edge likely | 618 |
| m2 / n4 | overflow, high and cmp unlikely | 470 |
| **n1** | **overflow and high unlikely** | **469** |
| n2 | overflow and cmp unlikely | 530 |
| n3 | high and cmp unlikely | 508 |

Source (`ir/spec*.json`, real builds):

| Variant | Change | Lines |
| --- | --- | ---: |
| v01 | price first | 544 |
| v02 | `vs` read inline | 906 |
| v03 | v01 + v02 | 593 |
| v04 | immediate `?` on `checked_mul` | 544 |
| v05 | v04 + `let-else` on `checked_add` | 544 |
| v06 | v04 + `match` on `checked_add` | 544 |
| v07 | no closure | 606 |
| v08 | closure with `if/else` return | 545 |
| v09 | `.map(\|s\| s/10_000)` | 775 |
| v10 | `match` with division in the Some arm | 537 |
| v11 | v10 + `match` on `checked_add` with the comparison in the arm | 470 |
| v12 | v10 + `match` on `checked_add` | 470 (line shift) |
| v13 | v12 + inline `vs` read | 530 |
| **v14** | **v12 with the line count preserved** | **469** |

## Next steps

1. Done in v14: the `match` forms keep the hints. pump-lo may want the same form for O0082's checked arithmetic.
2. Cap-selection order. The original selects the cap after the bps check and the raw quote.
   - This probably needs the cap chosen inside `sell_amounts`, which is shared with Legacy Sell; coordinate with pump-lo.
   - Then retry the late `vs` load.
   - Also try TECHNIQUES §7, the address-taken `native` flag, on the post-CPI native/token dispatch.
3. CPI and event tail regions (see README).

## Composition on 434 and post-CPI experiments (2026-10-27 ~22:40)

**Composed on 434.** `source.patch` (v14) applied to `mayhem-env/parent-434` (cp4 + O0073, rebuilt here to `e0d0d0c3…` / `828751f9…`):
- result: 434/441, 100 raw-local, 4,370 edges, 470 Source records, **no losses**, 0 `Stack offset` warnings;
- O0084: 17,896 bytes, **469** masked lines (unchanged from 433);
- hashes: stripped `30da05619050e81ddde80caeedae795df7dcb6bbccd37f70d7c7bbe7dbcbdfcb`, symbols `632fa065f63711b9cebe9f8b79842495b3cb8d44667435bf20eb6edce977b514`;
- record: `measure/measure-v14-on-434.json`.

**Post-CPI region (original 14376–14900): diagnosed, not closed.**
- In the original, the handler keeps the CPI `Result` (r7/r6) and builds the `PumpCpiFailed` AnchorError first. Only then (14800–14832) does it drop the CPI's `Err` payload.
- Ours (`if sell_v2(…).is_ok() {…} else {…}`) drops the `Result` at the end of the `if` condition, before building the error.
- Forms that keep the `Result` until after the error exactly fix this region, but every one tried also perturbs the CPI account-info construction just before the call. None beats v14's 469:

| Variant | Form | Bytes | Lines |
| --- | --- | ---: | ---: |
| w15 | `let outcome = sell_v2(…); if outcome.is_ok()` | 18,336 | 771 |
| w16 | `let outcome = sell_v2(…); match outcome` | 18,336 | 771 |
| w17 | `match sell_v2(…) { Ok(())=>Ok(()), Err(_)=>Err(error!(…)) }` | 17,960 | 696 (construction region at 3400–3700 reordered) |
| w18 | `if let Ok(()) = sell_v2(…)` (edition 2021 keeps scrutinee temporaries) | 17,960 | 696 |
| w19 | `.map_err(\|_\| error!(…))` | 17,960 | 696 |
| w20 | named `signer` + named `CpiContext` + match | 17,960 | 527 (post-CPI fixed; last three clones 72/168/176 rescheduled) |
| w21 | named `signer` + if | 17,936 | 589 |
| w22 | named `signer` + inline context + match | 17,960 | 527 |

- Interpretation: the original keeps both the inline `&[seeds]` temporary (no named signer) and a match-like extended-lifetime `Result`. The combination tried in w17 reorders a large block.
- Next: emit IR for w14 and w17 and diff them with `llc` to find which IR difference moves the construction region. It may be the extended lifetime of the `&[seeds]` temporary, or the placement of the new error block.
- **Late `virtual_sol_reserves` load:** v13 (inline read on top of v12) scored 530 against 470, still negative. Retry after the cap-order fix (pump-lo).
- **CPI construction region:** the account clone order (accounts-struct field offsets 176, 96, 24, 32, 80, 88, 40, 120, …, 72, 168, 176) equals the original's. The remaining differences there are register and stack scheduling.

## w23: post-CPI result drop order (2026-10-27 ~22:50) — committed

- **IR diff w14 vs w17** (normalized names): the functions differ only in block order. w17 moves the error-construction block to right after the call. The CPI construction IR is identical, so the machine differences there come from register allocation and block order.
- **No-JumpThreading diagnosis:** v14 scores 564 and w20 scores 666, both worse, so JumpThreading as in our default build matches the original.
- **w23 / w24:** the CPI `Result` is bound inside a block expression that ends right after the error is built (`if is_ok` and `match` versions are identical).
  - O0084: **17,912 bytes, 468 lines**; the post-CPI region takes the original shape.
  - 434/441, 100 raw-local, 4,370 edges, 470 Source records, no losses, 0 `Stack offset` warnings.
  - 7/7 SellV2 Source records equal; trade suites 6,636 cases, 0 mismatches, 0 non-compute log differences.
  - Stripped `8e8a25f926f24594692fd0a53135d81666bb623c1a53135b93a2b873e746624a`, symbols `c78f70390ae691a5a3e19192629d85230c8a904ef966044241d6067c46365431`.
- **Remaining post-CPI difference:** the original spills and reloads r8 on the Ok path (`ldxdw r8, [r10-1808]; ja @14848`); ours does not. This is register allocation.
- **Next targets:**
  - the event tail (original 15,240–16,700: field load order for the `SellEvent` tuple, including a 29-line block moved from 16,248 to 16,704);
  - the 10,000–11,000 CPI account-array copy order;
  - the late `vs` load, after pump-lo's cap reorder.

### Event-tail observation for the next step (w23, not yet acted on)

The event-tuple `if native {…} else {…}` field loads come out in a different order (original 15,224–15,700 vs w23 15,040–15,530).

| Arm | Original order | w23 order |
| --- | --- | --- |
| native | `global_params` +80/+72, then `mayhem_state` +48/+40, then `bonding_curve` +96/+80 | `mayhem_state` first, then `global_params`, then `bonding_curve` +80/+96 |
| non-native | `global_params` +96/+88, then the quote vault amount (`[a+56]+104`), then state, then curve, then quote-mint key words 24/16/8/0 | vault amount first, then global, then key words 8/16/24/0 |

- The original follows the source statement order of each arm; ours reorders.
- Next: emit IR for w23 and check whether rustc's IR keeps the source order. If it does, the reorder comes from scheduling, possibly from loads shared with the event construction after the tuple. Then try per-arm bindings or the TECHNIQUES §7 address-taken `native` flag.

## Lane mayhem-o84 (continuation, 2026-10-27 ~22:40)

Scratch: `claude-mayhem-work/o84/` (base `base-w23` = parent-434 + w23 patch; variant runner `tools/o84/var.py`, now race-free per build slot; packet refresher `tools/o84/pack.py`). Specs: `ir/o84-s*.json`.

### x02: signer seeds evaluated after the CPI account struct — committed

- **Finding.** The original reads `ctx.bumps.sol_vault` (Context `+34`, via the spilled ctx pointer `[r10-1792]`) at **10,016**, after all 26 `AccountInfo` clones and right before the struct copy into the `CpiContext`; it then builds `[b"sol-vault", &[bump]]` and the one-element signer slice there (10,024–10,096). w23 built the seeds at 3,096–3,176, before the clones (the named `bump`/`seeds` locals). This is the same evaluation-order gap as the main repository's `mayhem-signer-seed-order` packet found for Legacy Sell.
- **Source change.** Drop the `let bump=…;let seeds=…;` line (left empty, so line count and Source records are unchanged) and pass `&[&[b"sol-vault",&[ctx.bumps.sol_vault]]]` inline as the third argument of `CpiContext::new_with_signer`, with v14's `if sell_v2(…).is_ok() {Ok(())} else {Err(error!(…))}` form.
- **Result:** O0084 **17,944 bytes, 280 masked lines** (w23: 17,912 / 468). The whole 10,000–11,000 account-array copy region (124 lines) now matches; 434/441, 100 raw-local, 4,370 edges, 470 Source records, no losses, 0 `Stack offset` warnings, 7/7 SellV2 Source records equal. Trade suites: 14 families, 6,636 cases, 0 mismatches, 0 non-compute log differences. Stripped `d27e0e73…`, symbols `6df08c94…`.

| Variant | Post-CPI form (all with inline seeds) | Bytes | Lines |
| --- | --- | ---: | ---: |
| x01 | w23 block: `{let outcome=sell_v2(…); if outcome.is_ok() …}` | 17,992 | 348 (clone region 9,000–9,900 rescheduled; post-CPI right except `jeq`/`jne` direction) |
| **x02** | **v14: `if sell_v2(…).is_ok() {Ok(())} else {Err(error!(…))}`** | **17,944** | **280** |
| x03 / y05 | `match` / `if let Ok(())` | 18,024 | 404 |
| y01 / y02 / y08 | `.map_err(\|_\| error!(…))` (bound or `?`), `.or_else` | 18,024 | 404 |
| y03 / y06 | `if let Err(_) = … { return Err(…) }` / `match` with return | 17,912 | 501 |
| y04 | `let outcome=…; if outcome.is_err() { return … }` | 18,048 | 441 |
| y07 | `let outcome=…; let cpi_result = if outcome.is_ok() …` | 18,264 | 664 |

- x02 remaining by region: 0–2,000: 37 (price check), 2,000–4,000: 105 (`sell_amounts` cap selection, pump-lo's), 6,000–9,999: 18, 14,000: 14 (post-CPI `Result` drop order), 15,000–16,999: 100 (event tail), 17,000: 2.
- IR (x01 vs x02, `tools/o84/irnorm.py`): the two functions differ only in the order of the inlined `drop_in_place::<Result<(), Error>>` blocks and the `PumpCpiFailed` construction block. Block order alone moves the register allocation of the clone region.
