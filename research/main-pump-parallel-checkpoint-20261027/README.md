# Main Pump parallel research checkpoint

This preserves the main-contract sources, build records, signed comparison results, negative controls and in-progress work available when the snapshot was taken. It excludes rebuildable dependency/compiler caches, private keypair files, unrelated programs and the previously stopped token-owner experiment.

At snapshot time, the maintained, published source was [Round13](../../repro/pump/main-contract-round13-20261027/README.md): 653/1,035 normalized windows (63.1%), with whole-ELF identity unfinished. Round14 and Round15 are verified intermediate candidates; Round16 was still running its full regression at capture time. The manifest records those exact states.

**This is a research archive, not a selection of every included variant for use.** Failed and superseded controls remain evidence. In particular, an earlier V3 fee-waiver variant has known post-completion differences and remains unpromoted. `updates/` preserves its later714-case corrected successor, the validated legacy/V2 fee-waiver source, and the then-pending creation variant; `UPDATES.json` distinguishes these states. Individual passing corpora do not establish complete reconstruction.

The compressed snapshot is split into three parts for repository file-size limits. Verify all hashes and archive members with:

```sh
python research/main-pump-parallel-checkpoint-20261027/verify.py
```

To inspect the sources in a new directory without overwriting the current workspace:

```sh
python research/main-pump-parallel-checkpoint-20261027/verify.py --extract /tmp/pump-research-review
```

Extraction does not execute any included source. `MANIFEST.json` records all 5,201 files and their hashes, plus omitted active/generated files and the snapshot timestamp. Ongoing work after that timestamp remains separate until the next checkpoint.

`REMAINING-WORK.json` assigns all 218 unmatched Round41 windows to three parallel lanes, with initial source attribution and cross-cutting completion requirements. The later update receipts record completed Round16 and creation validation; the original snapshot retains its exact capture-time state.

The maintained source has since advanced to [Round41](../../repro/pump/main-contract-round41-20261027/README.md), with 817/1,035 matched windows and the complete validation recorded there. This archive retains its original capture-time contents.

[Later main-Pump follow-up research](follow-up-round18/README.md) preserves additional creation, V2-transfer and V3-fee work, including negative and pending variants. Its separate manifest and verifier retain the captured state without promoting those variants.

[Round22 follow-up research](follow-up-round22/README.md) preserves 8,939 additional main-contract research files, including validated, negative and unfinished controls. Its manifest and verifier bind four archive parts; inclusion does not promote a variant or establish full reconstruction.

[Round24 follow-up research](follow-up-round24/README.md) preserves 2,276 main-contract experiment files, including unpromoted controls and the funding counterexamples. Its archive manifest and verifier are separate from the maintained source selection.

[Round26 follow-up research](follow-up-round26/README.md) preserves 892 selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round27 follow-up research](follow-up-round27/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round28 follow-up research](follow-up-round28/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round29 follow-up research](follow-up-round29/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round30 follow-up research](follow-up-round30/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round31 follow-up research](follow-up-round31/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round32 follow-up research](follow-up-round32/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round33 follow-up research](follow-up-round33/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round34 follow-up research](follow-up-round34/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round35 follow-up research](follow-up-round35/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round36 follow-up research](follow-up-round36/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round37 follow-up research](follow-up-round37/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round38 follow-up research](follow-up-round38/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round39 follow-up research](follow-up-round39/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round40 follow-up research](follow-up-round40/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.

[Round41 follow-up research](follow-up-round41/README.md) preserves selected main-contract source, data-layout, receipt and provenance research files. Its independent manifest records the captured files; unpromoted trials are not selected by inclusion.
