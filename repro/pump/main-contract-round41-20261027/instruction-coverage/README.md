# Main Pump instruction evidence — sealed Round23

All **56 / 56 captured IDL families** have a reached case and an original successful transaction in the retained evidence. None is wholly absent or error-only. This establishes instruction-family coverage, not branch coverage or whole-contract correctness.

The evidence contains **16,260 paired rows**, including **14,826 rows with serialized original transactions**, representing **2,952 distinct literal signed transactions**. The remaining **1,434 rows** retain logs/state without transaction bytes. There are **13,857 distinct observable original receipts** under the documented fingerprint; this is not a count of complete unique starting states.

Using instruction bytes from reverified signed top-level transactions or recorded main CPIs backed by a reverified outer transaction, **44 families** have evidence and **43 have successful evidence**. The transaction-backed error-only family is: set_reserved_fee_recipients. Its successful cases exist in the log/state-only tier.

These 12 families have log/state evidence but no retained transaction-backed instruction bytes:

- `add_quote_mint`
- `close_user_volume_accumulator`
- `init_user_volume_accumulator`
- `remove_quote_mint`
- `set_max_curve_depth`
- `set_virtual_quote_reserves`
- `toggle_cashback_enabled`
- `toggle_create_v2`
- `toggle_mayhem_mode`
- `update_buyback_config`
- `update_creator_fee_config`
- `update_holder_reward_config`

Multi-hop and mayhem-parameter CPI evidence is explicitly separated from top-level main instructions. Eight bootstrap records are excluded. Malformed dispatch payloads and attempts rejected before main invocation remain unattributed rather than being assigned an intended family.

`REPORT.json` records per-family case/success/error counts and proof limitations; `coverage.csv` is the compact table. `OBSERVATIONS.json.gz` maps every paired row to discriminators and main-scoped invocation logs. Inputs are bound to the sealed checkpoint manifest. No transactions were generated, submitted or executed for this audit.

Reproduce from the repository root:

```sh
work/test-env/bin/python work/parallel-main-instruction-coverage/audit.py
```
