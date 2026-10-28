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
