# pump-lo progress (harvest log)

Lane: main Pump windows 0x340 … 0x65238, branch `claude/pump-lo-20261027`.
Each entry: base, lane commit, unstripped sha256, gained / lost windows (hex starts).

## Entries

### 1. Round36 official recipe — commit 3311aff01 (rebased onto Round37 as 7b350e34b)
- base: Round36 (`repro/pump/main-contract-round36-20261027`, 738/145, unstripped 9cc0982e…; reproduced
  byte-for-byte from its archived primary by `tools/r36_build.py`)
- patches: p02, p03, p04, p06 (p01 already in Round36)
- unstripped `886c7e6155fc5a1fe8927afa44fc0e5a570843a2a83c41a17ce3df170f32fcce`,
  candidate `2e24158e6e91c4887d9d60d7a19832f18b495f07fb67f733f79b0e848dfbc3db`
- result 743/145, matched text 906,872 B
- gained: 0x340, 0x2a8e8, 0x3b598, 0x3b738, 0x8cc58 · lost: none · raw lost: none · stack warnings: 0
- runtime: 18 suites / 3,657 cases, 0 mismatches; diagnostic audit 3,655 log-bearing, 0 mismatches
- evidence: `evidence/r36-g5/`

### 3. Round37 official recipe — commit 7b350e34b (rebased source, unchanged patches)
- base: Round37 (`repro/pump/main-contract-round37-20261027`, 744/175, unstripped 1a4b0664…; reproduced
  byte-for-byte from its archived primary by `tools/r36_build.py`)
- patches: p02, p03, p04, p06 (p01 already in Round37)
- unstripped `9e6eb914567433262b4fdb8cf01a24dabda7e1c361a2ac692bf4b4e0f63e6112`,
  candidate `19d90a81ecad9ccdc03cad16a6ff1f47e841c81a19ba0913c4c8f3400eb7a7b3`
- result 749/175, matched text 930,544 B
- gained: 0x340, 0x2a8e8, 0x3b598, 0x3b738, 0x8cc58 · lost: none · raw lost: none · stack warnings: 0
- runtime: 20 suites / 4,136 cases, 0 mismatches; diagnostic audit 4,134 log-bearing, 0 mismatches
- evidence: `evidence/r37-g6/`

### 2. Integration composite i1c (identity recipe) — commit 7b350e34b (patch p06)
- base: i1c 778/135, unstripped cf8094709b104e221942e1cfe121fffe5eec1ae96a77ad3eb46c5c8ddd31a495
- delta: p06 only (`evidence/i1c-p06/patch-vs-i1c.diff`); p03/p04 are already in i1c verbatim, p02 as
  `let amount=…`
- unstripped `20dd03324feb7bd58f57b32988ec71dcf2da6945fb12e2e4dc372ebc8a2b2600`,
  candidate `9d381c2acd2543e4af52168ced1e29e0f906e7d9c110ce11dd5bde2c7e57c0d3`
- result 779/135, matched text 987,752 B
- **gained beyond i1c: 0x2a8e8** · lost: none · raw lost: none · stack warnings: 0 (`runtime_valid: true`)
- evidence: `evidence/i1c-p06/`

### 0. Round25 (historical, pre-commit measurement; superseded by entry 1)
- base: Round25 720/123 (unstripped d36b2984…), patches p01–p04
- unstripped `b5ed5c32d4d48dd04c5d1e97837c72d646d1f5d83a47ae0c8aacdc254d43940b` (two identical builds)
- gained: 0x340, 0x29518, 0x3b598, 0x3b738, 0x8cc58 · lost: none
- runtime: 17 suites / 3,503 cases, 0 mismatches · evidence: `evidence/r25-g3/`
- p01 (0x29518) was integrated into Round36 verbatim; p02–p04 into the integration composite.

## Experiment log (negative controls and partial results)

| target | variant | result |
|---|---|---|
| 0x29518 | tfA helper-only / tfB helper+callers | both match; tfB adopted (closer handler shape) |
| 0x3cd50 prepare | preserve-result (baseline), and_then, match, is_err early return, if-let Err, `?`, named-local `?`, `\|\|` guard, nested if, swapped `&&` | none match; `?` gives the original guard order (tag first) but 1288 B with a split Err edge |
| 0x3b738/0x8cc58 | transfer exported only (R23) | 0x8cc58 matches; 0x3b738 needs the 3-arg helper exported too |
| 0x3b598 | E3 unused leading size, `minimum_balance(0)` | matches |
| 0x49708/0x56658 refund | inline seeds in call (p05) | frame matches; system_program load early |
| | `&a.mint.key().to_bytes()` let | load order and frame match; key copy pattern differs |
| | `a.mint.key().as_ref()` in let | E0716 (does not compile) |
| | inline + `&a.system_program` deref coercion | same as p05 |
| 0x2a8e8 | cv1 (`quote_token_program` as &AccountInfo, system_program unpromoted) | worse: argument shapes swapped |
| | cv2 (export collect, `system_program: &AccountInfo`) | prologue matches; extra event copy remains |
| | cv3 (= p06, + `emit!(event)` without clone) | **matches** |
| all `emit!(x.clone())` | global by-reference emit (40 sites) on i1c+p06 | 779, no gain, no loss (not adopted) |
| 0x3a7b8 sync | by-reference emit | 3552 B, 418/419 (one reload in the CPI error path) |
| | + no `ctx.accounts` alias (sync2) | unchanged 418/419 |

## Resume notes

- Tools: `tools/build.sh` (lane persistent-target build; byte-reproduces Round20/23/25/26),
  `tools/r36_build.py` (official Round36+ recipe, needs `--prepare-cache` on first use),
  `tools/measure.py` (packet normalizer, gains/losses vs packet inventory), `tools/sbfdiff.py`
  (aligned original-vs-candidate diff), `tools/origdis.py`, `tools/callers.py`, `tools/errsites.py`
  (Source coordinates), `tools/run_suites.py` (differential suites, test-env python).
- Integration session tools (read-only): `…/bfdcc76c-…/scratchpad/harness/fastbuild.py` (identity
  recipe; check `runtime_valid`/`stack_warnings`), `shared/score.py`, base at `base/current`.
- Remaining coordinate-free windows in this lane (unmatched in i1c): 0xd300, 0x1c880, 0x1db88, 0x22498,
  0x38fc0, 0x3a7b8, 0x3cd50, 0x414c0, 0x42618, 0x43060, 0x43ea0, 0x47e28, 0x48128, 0x48e10, 0x49708,
  0x4c158, 0x4e208, 0x4eb28, 0x502f0, 0x55d30, 0x56658, 0x58f58, 0x5a260 (see README residuals).
- Technique that keeps paying: compare the *call setup* of an unmatched caller with the candidate; an
  argument passed as a field address vs a loaded pointer reveals helper linkage (`pub` vs internal) and
  parameter types; a duplicated stack copy before `sol_log_data` reveals a needless `event.clone()`.
