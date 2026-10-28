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
| v01: price before scaled (`source.patch`) | 17,888 | 544 | 433 / 100 raw | none |

- v01 trade suites: 14 suites, 6,636 cases, 0 mismatches, 0 non-compute log differences.
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

## Next steps

1. Find a source form that keeps core's `unlikely` hint on `checked_mul` and `checked_add`, i.e. one whose Option Some arm is non-empty when SimplifyCFG runs (target: IR n1).
   - Then compare how the original Legacy Sell (O0082) and BuyV2 keep theirs.
   - Coordinate with pump-lo, since the same mechanism probably governs O0082's checked arithmetic.
2. Combine the late `vs` load (v03 form) with that fix, then attack the cap-selection order: load the quote-mint key words and the global-params base before the default/WSOL comparisons.
3. CPI and event tail regions (see README).
