# Independent creator-collection rent review

The 88 signed cases in this read-only review match the original against `work/parallel-main-collection-rent/build01/candidate.so`. No collection source files were edited. `RESULT01.json` records the findings and fixture limitations; `STATIC01.json` binds the original arithmetic and exact called methods.

The original V2 helper `0x2b490` uses saturating `recipient.lamports() + amount`, then checks that sum against `Rent::minimum_balance(recipient.data_len())`. The addition's unsigned carry selects `u64::MAX`, so overflow does not produce a Rust checked-add panic. Four overflowing recipient/amount cases reach System CPI and return its arithmetic-overflow error. Exact and just-below rent floors at data lengths 1, 165 and 1024 distinguish the actual-length rule.

Live FEES-owned recipients return 6050 before zero-amount, rent-floor and malformed token-source checks. Zero-lamport owner mutations are absent accounts in LiteSVM, so the initial zero-balance owner controls do not prove this; the separate 32-case live-owner set does. The initial Pump-as-creator executable controls fail an earlier mutability constraint. The ten later cases use already-loaded Token/Token22 program accounts and reach the executable-recipient early return, including zero amounts and an invalid token source. No executable flag or dependency ELF was altered.

The low-recipient rent skip also precedes native source-owner/data errors. With a funded recipient those same source mutations reach System CPI. Zero available amount preserves the no-fee log.

`SPECS01.json` carries the 88 executed case definitions, original input fingerprints, and source receipt for each. These are not claimed to be 88 unique incremental inputs. The collection owner will deduplicate them against existing suites and its own 64 cases.

Use `probe-selected.py --candidate CANDIDATE --output OUTPUT.json.gz --cases-file SELECTION.json`. Selection accepts either a list of records or `{ "cases": [ ... ] }` using records from `SPECS01.json`. The optional `--list-only` reports selected names. The two-case driver smoke covers both ordinary and loaded-executable dispatch and verifies the recorded original input hashes. All three original receipt files remain available without an unnecessary 88-case replay.
