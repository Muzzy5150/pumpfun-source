# Claim event CPI account-info boundary

The original claim body at `0x75308` passes one `AccountInfo` to `invoke_signed` at `0x76880`: the event authority. The previous reconstruction passed the event authority and the program account. `EVENT-CPI-ABI01.json` binds the raw call preludes and exact ELF hashes; the `r4` slice length is 1 in the original, 2 in the baseline, and 1 in this successor.

`source01` changes only `src/token_incentives/claim_token_incentives.rs`, removing the program account from the event CPI's account-info slice. The instruction's account metas, parsed context, worker, event bytes and error order are unchanged. The patch is `claim-event-account01.patch`.

All 528 targeted claim cases passed with matching signed transactions, accounts, token CPI data, events, diagnostics and invocation sequences. The set includes 30 new compound cases covering token-source depletion, frozen source/destination, claimed-total overflow and zero payouts. These confirm token-transfer failure precedes the post-transfer claimed-total addition, while zero payouts skip the token CPI.

Deduplication against the six authoritative Round32 claim suites (498 executions, 459 unique inputs) leaves 28 distinct additions. The fingerprint includes exact signed transaction bytes and canonical address-keyed non-null watched account state (owner, lamports, data, executable and rent epoch). `DEDUPLICATED-COMPOUND01.json` retains the two overlaps and the source receipts. The 28-case incremental driver was also replayed successfully and asserts every recorded original input hash. Its compatible corpus fragment is `additional-manifest01.json`.

The control preserves all 733 normalized and 119 raw matches of the R33 hybrid **identity layout**, without gaining a complete window. The claim body changes from 6,240 to 5,624 bytes, versus the original 5,920 bytes, and remains unmatched. This is an evidenced call-interface restoration, not a body-equality or whole-ELF claim. No padding, assembly, byte substitution or unrelated source changes were used. The parent must validate the combined final build and layout separately.
