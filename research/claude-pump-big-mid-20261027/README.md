# pump-big-mid (Claude lane, 2026-10-27)

This lane matches large unmatched main-Pump handler bodies in 0x65238..0xa0000
(`claude-pump-work/targets/big-mid.json`, minus the windows reassigned by the coordinator), on top of the Pump
session's genuine composite **g04** (806 normalized / 165 raw).

Each verified gain has its own directory, and every patch is body-only and moves no Source line. A gain
directory holds:
- `source.patch`, applied with `git apply -p1` inside a copy of `base/g04/pump` and checked on `base/L06/pump`;
- gzipped stripped and unstripped ELFs with `SHA256SUMS`;
- the `score.py` summaries for g04 and L06;
- runtime summaries for the changed handler's suites and the full 44-suite corpus;
- a stdlib `verify.py`, which passes with an empty `HOME`.

| gain | windows | g04 | L06 | runtime |
|---|---|---|---|---|
| `gain01-validate_new_mint/` | 0x68bd8 `QuoteControl::validate_new_mint` | 807 | 900 | 44/44 suites, 10,468 cases, 0 mismatches |

- `PROGRESS.md` is the working log: scope, per-window findings, IR proofs and open leads.
- `partial/0x746a8-incentives-mint-capture.patch` is earlier partial work handed to pump-big-lo, which closed
  that window in its gain02.
- `tools/` and `ir-experiments/` hold the build, score, IR-proof and runtime tooling (see PROGRESS.md).
