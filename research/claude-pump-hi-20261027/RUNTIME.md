# Runtime differential summary

All runs replay the **public 44-suite main-Pump corpus** (`scripts/pump_validate_all.py` `SUITES`).
Each case executes against the original `evidence/original/pump/deployed.so` and the candidate, through
the captured upgradeable-loader wrapper (`scripts/pump_with_captured_loader.py`). The harness scripts
are unchanged. `tools/run_suites.py` mirrors `scripts/pump_validate_parallel.py` per suite: it uses the same
`validate_result`, the same loader-receipt checks (program 36 B, ProgramData 10,485,760 B, unchanged ELF
prefix, zero allocation tail) and the same `pump_diagnostic_audit.audit`. The interpreter is
`REPO/work/test-env/bin/python` (3.12, solders 0.27.1).

| candidate | suites | cases | errors | paired diagnostic-log cases | diagnostic mismatches | loader loads |
|---|---:|---:|---:|---:|---:|---:|
| Round23 + dispatcher order + `update_global_authority` (`07f3f871…`) | 44 / 44 | 10,468 / 10,468 | 0 | 10,464 | 0 | 23,834 |
| Round23 + legacy buy const split (`b69f014a…`) | 44 / 44 | 10,468 / 10,468 | 0 | 10,464 | 0 | 23,834 |
| **Round25 + five lane changes** (`8a45886a…`, H3) | 44 / 44 | 10,468 / 10,468 | 0 | 10,464 | 0 | 23,834 |

These totals equal the frontier's own full-corpus totals (10,468 cases, 10,464 log cases). The per-suite counts,
harness hashes and report hashes are in `evidence/runtime-full-r23-gain.json`, `evidence/runtime-full-r23-buy.json` and `evidence/runtime-full-r25-lane.json`. The full 13 MB reports were kept
outside the repository.

An earlier partial run (8 suites, 4,306 cases, no failures) on the Round21 dispatcher-only candidate was
stopped when Round23 superseded it.

The focused Codex corpora (`additional.json.gz`, 116 suites) are driven by private harnesses under the
primary checkout's `work/` tree and run with that checkout as cwd. They were not executed from this read-only lane.
