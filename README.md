# pumpfun-source

Reconstructed Rust source for Pump.fun's Solana programs, with captured binaries,
reproducible builds and local differential tests.

**Progress as of 27 October 2026: the Pump Fees research reconstruction reproduces its
complete meaningful ELF byte for byte; the other three core programs still differ from their
captured binaries. The selected Donation Relay reconstruction reproduces its complete meaningful
ELF and, through a separate loader deployment, its captured payload.**

## Current progress

**Mayhem: 436/441 function windows matched (98.87%), including both Legacy trade
bodies; five remain (1.13%). Unmatched code is 72,192 bytes (10.21%).**
See the [completion review](docs/MAYHEM-COMPLETION.md) for all five bodies and the
distinction between 141 raw-equal and 295 normalized-only matches.

**PumpSwap: 656/785 function windows matched (83.6%); 129 remain (16.4%). Matched windows cover 71.1% of original executable text, leaving 335,928 bytes (28.9%).**

These are binary-coverage measurements. Full call/data/relocation identity, original build provenance and uncovered behavior remain open. The [remaining-work review](repro/pump_amm/incentive-order-recovery-20261027/remaining-audit/README.md) lists all 129 unmatched windows. The latest checkpoint also resolves all 128 incentive error-order counterexamples in the new 1,730-case matrix.

[Current main-Pump parallel research snapshot](research/main-pump-parallel-checkpoint-20261027/README.md) preserves the verified intermediates and in-progress source beyond the maintained checkpoint.

**Main Pump: 78.9% of function windows matched; 60.6% of original text covered. Complete reconstruction remains unfinished.**

Reproduce the selected Pump ELF with its [archived Rust/linker recipe](repro/pump/main-contract-round41-20261027/reproduce.py).



<!-- MAIN-PUMP-REMAINING:BEGIN -->
### Main Pump remaining work

The maintained checkpoint matches **817/1,035 function windows (78.9%)**;
**218/1,035 (21.1%) remain unmatched**. Matched windows cover
**1,085,456/1,792,208 code bytes (60.6%)**, leaving **706,752 bytes
(39.4%) uncovered**. Of the matched windows, 203 are raw byte-equal
and 614 require normalization of specified call/address operands.

These are binary coverage percentages. A defensible percentage of engineering
work remaining is not yet known. Whole-ELF equality remains unproved. The corpus
checks structured Anchor/panic diagnostics and ordered raw logs within complete
recorded main invocations. It requires zero non-filename mismatches and reports
651 remaining source-filename differences.

Remaining work is to recover the unmatched main-contract bodies and validation
paths, reproduce referenced data and relocations, and establish the original
compiler and target-library provenance. This checkpoint restores observed ordinary
messages and CPI ordering and corrects cashback quote-program error precedence.
The retained corpus does not establish complete behavior or original build identity.
A newer signed compound-input witness still exposes a `set_params` zero-recipient
versus rent-check precedence mismatch. Its fix is staged for the next checkpoint;
it is outside the frozen Round41 regression corpus.

The [main-contract queue](research/main-pump-parallel-checkpoint-20261027/REMAINING-WORK.json)
tracks the open bodies. The [selected checkpoint](repro/pump/main-contract-round41-20261027/README.md) binds the
reported metrics and validation evidence. This review is limited to the main Pump
contract.
<!-- MAIN-PUMP-REMAINING:END -->

Across the latest verified checkpoints, **2,986 / 3,338 inferred function windows
match (89.5%)**. Their matched windows cover **4,098,256 / 5,213,128 original text
bytes (78.6%)**. **Two of five programs have complete meaningful-ELF identity**;
three of the four core contracts still differ from their captured binaries.

These percentages measure bounded binary-recovery progress, not a claim that
89.5% of the engineering work is finished. Complete reconstruction also requires
all remaining code, calls, data, relocations and build provenance.

| Latest verified checkpoint | Matched windows | Matched % | Raw-equal bodies | Normalized only | Unmatched | Whole ELF equal |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| [Pump Round41](repro/pump/main-contract-round41-20261027/README.md) | 817 / 1,035 | 78.9% | 203 | 614 | 218 | No |
| [PumpSwap / AMM](repro/pump_amm/incentive-order-recovery-20261027/README.md) | 656 / 785 | 83.6% | 148 | 508 | 129 | No |
| [Fees research](research/claude-fees100-crank-donation-20261027/README.md) | 585 / 585 | 100.0% | 585 | 0 | 0 | **Yes** |
| [Mayhem qualified research](research/mayhem-current436-composition-20261027/README.md) | 436 / 441 | 98.9% | 141 | 295 | 5 | No |
| [Donation Relay](repro/donation-relay/canonical-exact-selection/README.md) | 492 / 492 | 100.0% | 492 | 0 | 0 | **Yes** |
| **Total** | **2,986 / 3,338** | **89.5%** | **1,569** | **1,417** | **352** | **2 / 5** |

“Windows” are inferred original machine-function ranges, including framework and
runtime helpers. Complete normalized matches mask specified call/address
operands; they do not prove the referenced callees or data match. Each original
window counts once. Raw equality means that local body is byte-equal, not that
the whole program is identical.

| Checkpoint | Text bytes in matched windows | Text covered | Unmatched text |
| --- | ---: | ---: | ---: |
| Pump Round41 | 1,085,456 / 1,792,208 | 60.6% | 706,752 |
| PumpSwap / AMM | 826,112 / 1,162,040 | 71.1% | 335,928 |
| Fees research | 799,648 / 799,648 | 100.0% | 0 |
| Mayhem research | 634,552 / 706,744 | 89.8% | 72,192 |
| Donation Relay | 752,488 / 752,488 | 100.0% | 0 |
| **Total** | **4,098,256 / 5,213,128** | **78.6%** | **1,114,872** |

Pump and AMM rows describe the verified maintained sources. Fees and Mayhem rows
are the latest qualified research frontiers, distinct from their maintained
selections in [repro/status.json](repro/status.json). The maintained Mayhem initializer now has its own [current-source build and
signed validation](repro/mayhem/initializer-current-20261027/README.md), separate
from the larger research frontier. Upstream Relay's canonical selection remains
the authority for its exact result.

Relay reproduces all **818,280 meaningful ELF bytes**. Its separate signed local
loader replay reproduces the **830,448-byte captured payload**, including 12,168
loader-allocated zero bytes. This does not establish the original historical
source or build recipe.

The latest [Metaplex research packet](research/claude-deps-metaplex-20261027/README.md)
matches all 707,448 bytes of the captured meaningful ELF and all 1,251 function
windows. A separate 86,543-byte zero extension matches the captured allocation;
it is not part of the stripped compiler artifact. This dependency result remains
unpromoted and does not change the core-program totals above. The [parallel-lane
review](research/claude-lanes-review-20261027/README.md) records the other packets
and their baseline/validation limits.
The [independent Utilize recovery](research/metaplex-utilize-exact-recovery/README.md)
adds the retained unstripped compiler output, empty-target build/dependency
receipts and two separately signed replays of that same 147-case corpus. Its
alternative source is an unpromoted compiler-context diagnostic.

## Behavior and remaining work

**Mayhem now has 436/441 complete normalized matches (98.87%), leaving five
bodies (1.13%) and 72,192 original text bytes (10.21%) unmatched.** The
[qualified composition](research/mayhem-current436-composition-20261027/README.md)
adds the complete Legacy Buy and Legacy Sell bodies, preserves all 141 raw-equal
bodies and raises direct-call closure to 429 windows.
Two combined builds agree; full trade, initializer, sweep and rate verification
checks 18,534 signed records across overlapping scopes. Whole-ELF identity is
still unfinished.

The complete Buy/Sell quotes and initializer retain their bounded typed-data
checks, and the BpfWriter/ExtendAccountEvent origins remain repaired. O0073 and
O0075 now have complete normalized bodies. Every remaining function is listed
in the [completion review](docs/MAYHEM-COMPLETION.md) and the
[441-row inventory](research/mayhem-current436-composition-20261027/inventory.tsv).
Data, indirect calls, global layout and original build provenance remain open.
The [code-reference review](research/mayhem-current434-code-reference-closure-20261027/README.md)
verifies all 48 relocated code-address sites in matched bodies and preserves the
425-window closure on the preceding 434-window artifact. Its separate
[conditional formatting proof](research/mayhem-current434-format-route-20261027/README.md)
resolves three indirect sites across 25 explicit tag inputs under stated
allocation/writer assumptions. The [Custom branch proof](research/mayhem-current434-custom-format-route-20261027/README.md)
adds three tuple-dispatch sites and follows the payload pointer to the numeric
formatter. Both proofs remain bound to the preceding 434 artifact. General
indirect-call and data identity remain unresolved.

The [current selected-data checks](research/mayhem-current436-selected-prefixes-20261027/README.md)
preserve all 429 closed windows while checking 486 Source coordinates, 48 code
addresses and 119 references to 32-byte prefixes. They reject 22 ambiguous
counterpart pairs without claiming complete data or indirect-call identity.

The [native historical-macro composition](research/mayhem-native-current432-composition/README.md)
also reproduces 432 normalized windows and 85 raw-local matches in its own
recipe. Its earlier Legacy Buy source remains distinct. The later
[current native ownership composition](research/mayhem-current-native-ownership-composition/README.md)
preserves the closer Legacy Buy body and passes 486 fresh pairs; the independent
[native allocator composition](research/mayhem-current-provider-closure-20261027/README.md)
confirms 422 direct-closed windows and 6,636 fresh pairs. These default-order
85-raw results are not added to the qualified 141-raw count.

The [portable Linux recipe](research/mayhem-clean-linux-build-20261027/README.md)
reproduces both full artifacts across two fresh dependency builds. It preserves
432 normalized / 84 raw-local bodies with default section order. Rechecking
both unchanged-parent outputs retains the [same 414-window direct-call relation](research/mayhem-direct-call-closure-20261027/README.md#fresh-linux-follow-up);
the macro source change above supplies the subsequent allocator repair.

The [AMM handler shape controls](research/mayhem-amm-handler-shape-controls-20261027/README.md)
isolate account-copy expansion, arithmetic error flow and native-key evaluation
order. Nine source/compiler controls preserve their 432-window search baseline;
one separately compiled variant also preserves all 100 qualified raw matches.
They add no complete function match and have no fresh runtime qualification.

The later [AMM Sell CFG packet](research/mayhem-amm-sell-cfg-recovery-20261027/README.md)
preserves two closer partial bodies, including an equal-length 17,312-byte
control. Both retain 249 corresponding control-flow blocks and all 47 ordered
callee shapes, but still differ in event construction. Each has its own 18-pair
signed replay. These remain partial 432/89 search artifacts and add no match to
the qualified 434/141 checkpoint.

The [Legacy/V2 ownership packet](research/mayhem-trade-ownership-current-20261027/README.md)
preserves the larger BuyV2/SellV2 source reconstruction and two distinct Legacy
Sell controls. Its V2 composition passes 48 signed pairs; the late-bump and
event-order controls have static evidence only. All handlers remain partial.

The [current-parent AMM event composition](research/amm-current-event-capture-20261027/README.md)
adds the complete 1,784-byte normalized sell-event body, retaining all prior
matches. Two builds agree; all 17,462 maintained cases and 26 focused event pairs
pass. Its 641-window research artifact remains bound to its former
640-window parent; the maintained 647-window checkpoint is reported above.
The parent's other supplemental matrices were not rerun on this artifact.

Pump Round41 passes 10,468 full cases plus 7,642 focused executions, with 18,106
paired diagnostic-log cases. AMM passes 17,462 full cases plus the separate
account, fee, CPI, boundary and error-order matrices recorded in its checkpoint.
The [independent Pump/AMM migration-pair replay](research/pump-amm-migration-composition/README.md)
pairs the frozen Round34 Pump and AMM643 artifacts across 65 signed inputs
in four combinations: 260 executions and 195 comparisons, with no differences.
It does not qualify the newer AMM647 composition.
These corpora overlap and must not be summed as unique scenarios. Tests use
captured programs in local VMs; they do not establish current-chain acceptance.

The [current Mayhem initializer recovery](research/mayhem-initializer-current-recovery-20261027/README.md)
adds the complete 960-byte normalized initializer, including its five immediate
callees and four typed data references. Two current-framework builds agree;
6,636 fresh trade pairs and 69 initializer pairs pass, with ten successful
creations. That checkpoint has 430/441 normalized matches and eleven unmatched
windows. The [complete per-window inventory](research/mayhem-initializer-current-recovery-20261027/inventory.json)
separates raw-equal, normalized-only and unmatched bodies. A separate historical
macro composition reaches 430/141, kept outside the current row.

The [current-source Legacy Buy ownership composition](research/mayhem-current-ownership-composition-20261027/README.md)
preserves that 430/100 frontier and improves the partial handler to 13,784 bytes
against 13,848 original bytes. Its 50 immediate callee shapes and seven Source
records agree; two builds and 486 signed replay pairs pass. The full body remains
unmatched, so this adds no window to the table.

The earlier [Mayhem trade-origin and validator recovery](research/mayhem-trade-origins-validator/README.md)
adds the complete 1,296-byte normalized quote validator with its eight immediate
callees and fourteen typed data references checked. It reaches 429 normalized
and retains all 100 raw matches. Three partial trade handlers now reproduce 21
Source records and three CPI error origins. Two qualified builds agree, and 65
fresh case pairs pass. At that checkpoint twelve bodies, an allocator specialization and
whole-ELF identity remained unresolved; older runtime receipts keep their original
artifact bindings.

The [BuyV2 sizing follow-up](research/mayhem-sizing-panic-recovery/README.md)
preserves that frontier and restores the original typed sizing failure for all
three quote families. Its 6,636 fresh trade comparisons agree in functional
results and complete non-compute logs. The BuyV2 body remains unmatched.

A [same-IR compiler diagnostic](research/mayhem-host-llvm-comparison/README.md)
produces identical Mac and Linux LLVM objects for one earlier initializer
control. This narrows that investigation without adding a function match.

The [quote backend replay](research/mayhem-quote-backend-replay-20261027/README.md)
holds the saved Rust IR fixed: v1.54 reproduces the reference helper's masked
1,120-byte body, while v1.52 emits 1,288 bytes and v1.44 rejects the IR. The
original quote helper still differs in sixteen instruction slots; this
diagnostic adds no recovered function or runtime coverage.

An [allocator-context experiment](research/mayhem-allocator-context/README.md)
reproduces the missing reserve helper through a zeroed-allocation probe. It
identifies a compiler condition to recover through justified source; the probe
remains a diagnostic and the current reconstruction counts are unchanged.

The [historical parser follow-up](research/mayhem-allocator-parser-provenance/README.md)
reproduces that allocator form with an earlier Anchor event-parser template and
current event types. It is a mixed-source compiler experiment; original Mayhem
source remains unproven. The [earlier current-source composition](research/mayhem-control-work-20261027/README.md)
now preserves all 429 normalized matches and reaches 139 raw-local bodies,
with one additional matching allocator call. Repeated native builds agree;
6,636 fresh trade and 69 initializer comparisons pass. Its 39 additional raw
bodies cover 33,968 original text bytes. This remains a diagnostic, so the
established checkpoint counts in the table above are unchanged.

The [current-source historical macro composition](research/mayhem-historical-macro-current-20261027/README.md)
reproduces that same artifact with the complete historical Anchor macro and
historical event definition, removing the manually rendered parser. Two native
root builds agree; the upstream-gated control reproduces the parent. The target
runtime is still current Anchor, and no new original matches or target executions
are claimed.

The latest [Fees Crank recovery](research/claude-fees100-crank-donation-20261027/README.md)
completes the Pump Fees research reconstruction. Together with the
[CreateDonation recovery](research/claude-fees100-create-donation-20261027/README.md), the Sweep recovery
([#308](research/fees-sweep-integration/README.md), with the same source shape first published in
[#299](research/fees-sweep-entry-recovery-20261027/README.md) and
[#301](research/fees-sweep-integration-20261027/README.md)) and the earlier recoveries, all 585 original
functions match normalized and raw. The stripped canonical Linux build is byte-identical to the captured
program's complete 873,256-byte meaningful ELF; the remaining capture bytes are zero loader allocation. Two
fresh builds agree and all 17,331 runtime comparisons pass. The
[whole-ELF end-state proof](research/claude-fees100-whole-elf-endstate-20261027/README.md) shows why the
existing layout recipe needed no further change. The qualified source is materialized from these research
packets; the maintained `programs/pump-fees` tree is a separate build target, and the historical source
spelling and build provenance remain unproven.

The [Fees frame and inlining archive](research/fees-frame-inline-research-20261027/README.md)
preserves another 1,675 new or updated research files beyond the earlier
checkpoints. It includes a current-source Crank build, measured stack-lifetime
improvements, and Create call-graph recovery. The full recovery chain contains
88,263 current files. These experiments retain their individual status and add
no accepted matches.

The latest [PumpSwap incentive ordering and liquidity structure recovery](repro/pump_amm/incentive-order-recovery-20261027/README.md) retains 656 windows and 148 raw bodies while fixing all 128 new incentive error-order counterexamples. All 1,730 new signed boundary cases, 17,462 core cases and retained supplemental suites pass; 129 AMM windows remain. Liquidity Context and LegacyBuy source organization are also restored without claiming new complete body matches.

Remaining priorities are the 218 Pump, 129 AMM and 7 Mayhem unmatched
windows; deeper call/data/relocation identity; original build provenance; and
uncovered behavior such as authentic fixed-admin AMM `create_config` success.
The historical [150-handler audit](repro/reconstruction-audit-2026-10-26/handlers.md)
remains a separate bounded classification; newer function matches do not
retroactively certify every handler.

See [remaining work](docs/REMAINING-WORK.md),
[current reconstruction review](docs/RECONSTRUCTION-STATUS.md) and the
[research history](docs/BYTE-IDENTITY-PROGRESS.md) for evidence and limitations.

## Dependencies

| Dependency | Current byte result |
| --- | --- |
| SPL Token | 108,600 / 108,600 captured bytes reproduced (100%) |
| Token-2022 | 611,056 / 611,056 meaningful ELF bytes reproduced (100%); full 1,382,016-byte allocation requires 770,960 separately added zero bytes |
| Associated Token Account | 105,032 / 105,032 bytes reproduced (100%) by two non-historical research recipes; authentic recipe and selected promotion unresolved |
| Metaplex Token Metadata | Research reproduces all 707,448 meaningful compiler-ELF bytes; an independent local loader replay reproduces the 793,991-byte payload. Maintained selection and historical provenance remain separate. |

[Dependency evidence and selection status](repro/dependency-status.json).
Allocation-image equality is separate from unchanged compiler-output equality.

## Quick start

Use Python 3.12. Clone without line-ending conversion to preserve evidence hashes:

```sh
git clone --config core.autocrlf=false https://github.com/lalalune/pumpfun-source.git
cd pumpfun-source
python3 scripts/verify_evidence.py
python3 scripts/test_tooling.py
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/local_validation.py
```

Build and compare instructions: [tooling guide](docs/TOOLING.md) and
[scripts index](scripts/README.md). Source is in `programs/`, captured comparison
inputs in `evidence/`, and reproducibility records in `repro/` and `research/`.
See also [scope](docs/SCOPE.md), [security policy](SECURITY.md) and
[audit scope](audit/AUDIT.md).

## License

This repository's own code and documentation are released under the
[MIT License](LICENSE). Third-party and vendored materials (for example the
Apache-2.0 Solana SDK files under `programs/pump-amm/vendor`, imported research
and retained crate archives) keep their original licenses, and upstream Pump IDLs
and binaries remain with their original authors.
