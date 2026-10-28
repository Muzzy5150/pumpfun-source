# Native creator recipient rent gate

Isolated main-Pump correction in lib.rs and creator/collect_creator_fee.rs. A positive native payment is skipped when recipient lamports plus the payment (saturating) would remain below rent exemption for the recipient data length. Owner, executable, and zero-fee precedence is retained; token payments are unchanged.

425 comparisons and a separate128-case deduplicated replay pass, including strict diagnostics, plain messages and CPI order.18 observed baseline differences are corrected. The full733 normalized-window set is preserved; no new byte window or qualified raw-layout claim is made.

See RESULT01.json, CLI-MANIFEST.json and DEDUPLICATION.json. The independent88-case review is retained at ../parallel-main-collection-rent-review. Source01 and all reports are frozen for parent composition.
