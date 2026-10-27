# PumpSwap lane amm-mid (original windows 0x3d828 … 0x724a0)

Review status: this is an unpromoted research proposal. Review `fdc55bfc2`
found that the first revision shipped no candidate ELF, so its match claim
could not be recomputed. This revision answers that finding. It ships both
ELFs for every claimed result, rebases onto the 623 frontier, and adds
`verify.py` to recompute the claims. Promotion into a selected checkpoint
remains the integrating session's decision.

Research packet from the parallel byte-identity effort. It is rebased on the
published AMM frontier
[`repro/pump_amm/account-context-recovery-20261027`](../../repro/pump_amm/account-context-recovery-20261027/README.md)
(candidate `badc9498…`, 623/785 normalized, 128 raw, 162 unmatched). The first
result was measured on the earlier `native-fee-cpi-recovery-20261027` frontier
(599). That evidence is kept under `gains/01-event-context-captures/history-599/`.

The maintained `programs/pump-amm/src` is **not** modified on this branch.
CI binds it to the frontier's canonical source (`verify_pump_amm_checkpoint.py`
asserts `current_source_verified`). The recovered change ships here as
[`source.patch`](source.patch), cumulative against the 623 canonical source.
Apply it with `git apply` at the repository root. The full changed file is
under [`source/`](source).

## Result

| | Frontier `badc9498` | This packet |
| --- | ---: | ---: |
| Normalized windows | 623 | **624** |
| Raw-equal windows | 128 | 128 |
| Unmatched windows | 162 | 161 |
| Lost windows | — | none |

Newly matched original window: **`0x52c58`** (1,784 bytes, the sell event
builder `create_sell_event`). On the earlier 599 frontier, the same change
gave 599 → 600, also with no losses.

The candidate was built with the frontier's authenticated Linux v1.44 SBPF
recipe:

- stripped SHA-256: `a11fbac3b2f5f7279541015a85bf09f00296cf7b26027a82b9fe73b67a69ebd1`
- unstripped SHA-256: `6627417e3fb9737d9a707486be663ec85651d64c8e45efdb1a59466d3ef27f69`

Both ELFs ship gzipped in `gains/01-event-context-captures/candidate/`, with
`sha256.json`. The `measure.py` output is in `measurement.json.gz`.

`python3 -B research/claude-amm-mid-20261027/verify.py` checks every shipped
candidate. For each, it decompresses the ELFs, checks the hashes, re-runs the
repository measurement tool and re-measures the named frontier. It then prints
gained and lost windows and checks that `source.patch` reproduces the shipped
source files.

## Recovered source cause (0x52c58)

The frontier builder differed from the original by one instruction. The
`lddw r4, 1_000_000_000_000_000` feeding the mayhem `base_supply` phi was
scheduled six slots early, ahead of the three `context.user*` field-address
computations (`r9+96/+64/+32`). Tracing the codegen pipeline for this one
function showed the mechanism:

- MachineSink moves the phi-constant materialization into the block that ends
  at the mayhem branch. It inserts at the top of the target block and keeps
  the relative order of instructions sunk together.
- In the frontier, the three field addresses were already defined in that
  block, so the constant landed above them.
- In the original, the three addresses come from the entry block, before
  `Clock::get()`. They are sunk along the same chain after the constant, so
  they land above it: `+96, +64, +32, 1e15, +8`.

Re-running `llc` on the crate's own optimized IR, with only those three
`getelementptr`s moved into the entry block, reproduces the original window
exactly. The corresponding ordinary source captures the user keys with the
other context fields, before the fallible clock read:

```rust
let pool = context.pool;
let global_config = context.global_config;
let base_supply = context.base_supply;
let user = context.user;
let user_base_token_account = context.user_base_token_account;
let user_quote_token_account = context.user_quote_token_account;
let timestamp = Clock::get()?.unix_timestamp;
```

The same captures in `create_buy_event`, before its checked addition, remove
the buy builder's displaced `pool+8` spill sequence. That leaves `0x52070`
with exactly one difference: the source-line immediate of its `Overflow` site
(original `trade_v2.rs:515`), so `0x52070` is not counted here. The change is
behavior-neutral, because the copied keys come from an immutable by-value
context.

## Validation

All suites ran against the 623-rebased candidate (`a11fbac3…`) using
`work/test-env/bin/python` with the frontier's harnesses and observer:

| Suite | Cases | Mismatches |
| --- | ---: | ---: |
| `scripts/pump_amm_trade_v2_differential.py` (observed) | 870 | 0 |
| `scripts/pump_amm_buyback_differential.py` (observed) | 369 | 0 |
| `scripts/pump_amm_cashback_differential.py` (observed) | 146 | 0 |
| `probe_sell_events.py` (holder, mayhem, fee and reserve modes) | 10 | 0 |
| `probe_buy_events.py` (`buy_v2`, `buy_exact_quote_in_v2`) | 16 | 0 |

Only the three trade_v2 executors call the two builders. The same five
suites also passed on the 599-based candidate `5e853b84…`. Transaction
sidecars and gzipped receipts are in each gain's `runtime/` directory.

## Residual diagnosis in this range

At the 623 frontier there are 63 unmatched windows in range (the frontier
newly matched `0x724a0`). 62 remain with this packet. They fall into these
groups:

- **Source-line immediates only** (29 windows on 623; full list in PROGRESS.md). Every remaining
  difference is the `line` stored by an `error!` or `require!` site, and the
  line deltas within each function already match. Examples:
  - Pool helpers `0x6b780`, `0x6ba68`, `0x6bf50`, `0x6c328`, `0x6c768` and
    `0x6d128` (`state/pool.rs` lines 386–484).
  - GlobalConfig setters `0x61d68`, `0x62c40`, `0x62e68` and `0x63778`.
  - The 520-byte `error!` closures `0x40100`, `0x446a0`–`0x450d8`,
    `0x4bf30`–`0x4c548` and `0x57e20`.
  - `0x50ca8`, `0x516e0`, `0x6f608`, and now `0x52070`.

  On the 599 frontier, 121 of 186 unmatched windows carried such sites, and
  only 3 matched windows did. Codex's pool-source-organization lane reached
  the same conclusion: these need the original preceding file contents, not
  padding, so they are not attempted here.
- **In flight in Codex work dirs** (skipped): `0x58028` (pool-prepare),
  `0x4efb8`, `0x4f1d8` and `0x62e68` (buyback validator), `0x6db20` and
  `0x6f3c8` (incentive state), and `0x44ab0` (fee context).
- **Structural**: large handlers that also carry line sites — `0x3dbc0`,
  `0x40a08`, `0x45940`, `0x49b50`, `0x4c750`, `0x53350`, `0x54a20` and
  `0x56710`.

See [PROGRESS.md](PROGRESS.md) for the final per-window residual diagnosis, including the fully diagnosed
but unclosed `0x51d08` (IR block order), and `residual-table-623.json` for every remaining window.
[`negative-controls/negative-controls.json`](negative-controls/negative-controls.json)
lists every variant tried.

## Reproduce

```sh
# 1. stage the frontier workspace from canonical source + this patch (scratch checkout)
git apply research/claude-amm-mid-20261027/source.patch
python3 repro/pump_amm/account-context-recovery-20261027/workspace_recipe_v2.py stage \
  --source-root . --output /tmp/amm-stage
# 2. strict offline Linux v1.44 build (frontier recipe; lane copies mounted at the
#    frontier's recorded container paths; holds the shared sbf + podman locks)
python3 research/claude-amm-mid-20261027/tools/linux_build.py --source /tmp/amm-stage --output /tmp/amm-build
# 3. measure with the repository tool
python3 repro/pump_amm/focused-diagnostics-20261026/measure.py \
  --candidate /tmp/amm-build/artifacts/pump_amm_recovered.so \
  --symbols /tmp/amm-build/artifacts/unstripped.so --output /tmp/amm-measure.json
```

`tools/linux_build.py` mirrors the container paths recorded in a frontier
`build-comparison.json` (`--frontier-record`, default: the 623 frontier).
Building the unmodified 599 frontier source with it reproduced `a4b978ee…`
(unstripped `784592ce…`) byte-for-byte. Native macOS v1.44 builds
(`tools/native_build.sh`) produce identical bodies for every symbol except the
TypeId-bearing `type_id` helpers, all of which lie outside this range. Native
builds were therefore used only for iteration.
