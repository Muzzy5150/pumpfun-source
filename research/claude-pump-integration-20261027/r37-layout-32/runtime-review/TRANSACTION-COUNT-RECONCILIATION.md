# L32 signed-transaction count reconciliation

The two published counts use different traversal scopes over the same immutable
`full.json.gz` receipt. Neither represents a different runtime corpus.

- **18,268 occurrences / 2,407 distinct:** transactions stored directly as
  `original.transaction_base64` or `candidate.transaction_base64` on a paired case.
- **18,284 occurrences / 2,409 distinct:** every recursively stored signed
  transaction, including bootstrap transactions nested under an outcome.

The 16 additional occurrences are the original and candidate copies of one
bootstrap transaction in each of `creator_distribution/cases/278` through
`creator_distribution/cases/285`. Cases 278–281 use transaction SHA-256
`c04a45d122e212ee0dcea275925aa393ffc17def4e08218e03ab4cda428b3d5b`;
cases 282–285 use
`b214cc90b946aa462fd6e1fac40b830d7328a1062bdbbd24e2663e4058ccaf24`.
Both are stored at `bootstrap_transactions/0/transaction_base64` and are absent
from the top-level transaction set.

`audit_saved_runtime.py` reports both scopes and cryptographically verifies the
recursive 18,284-occurrence set. It does not rewrite this evidence package or
submit any transaction.
