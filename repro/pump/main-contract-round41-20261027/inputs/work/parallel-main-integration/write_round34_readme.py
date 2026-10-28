"""Write the evidence-bounded Round34 checkpoint description."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'repro/pump/main-contract-round34-20261027'
cp = json.loads((P / 'CHECKPOINT.json').read_text())
n, total = cp['normalized_windows'], cp['original_windows']
matched, size = cp['matched_text_bytes'], cp['original_text_bytes']
logs = cp['full_log_cases'] + cp['additional_log_cases']
text = f'''# Main Pump verified checkpoint — Round34

The maintained main contract matches **{n:,} / {total:,} original function windows ({100*n/total:.1f}%)**, including **{cp['raw_windows']} raw byte-equal bodies**. Those windows cover **{matched:,} / {size:,} original text bytes ({100*matched/size:.1f}%)**. The closed direct-call subset contains {cp['closed_call_windows_without_data']} windows and excludes data references. Normalization masks specified call/address operands; it does not establish referenced data or whole-program identity. **Whole-ELF identity remains false.** These figures measure binary coverage, not the fraction of engineering work completed.

The captured-loader regression passes **{cp['full_suites']} suites / {cp['full_cases']:,} cases** and **{cp['additional_suites']} focused suites / {cp['additional_cases']:,} executions**, with **{logs:,} matching paired diagnostic-log cases**. These corpora overlap. Diagnostics exclude source coordinates and compute usage. Tests use captured upgradeable-loader dimensions in local VMs. The verifier requires serialized transaction bytes for every original/candidate result and rechecks signatures and instruction attribution. No current-chain acceptance is implied.

Round34 restores the unswept-creator-fee admission guard in both distribution handlers, the native recipient rent floor in both creator-collection handlers, and the claim event CPI’s original one-account slice. The claim body remains unmatched. The rejected QuoteControl source experiment is retained as research only; its useful capacity cases join the corpus. The four additions provide 253 executions: 61 distribution, 128 collection, 28 claim and 36 QuoteControl cases. Collection controls cover zero fees, recipient account length, saturation/overflow, real executable accounts and live ownership precedence. The 36 capacity inputs are distinct from the prior full QuoteControl suite; broader corpora may overlap. No new function-window count is claimed.

The opt-in `linux-v1.44-sbf` build profile combines the pinned native macOS v1.44 compiler and host libraries with exactly 25 SBF target libraries from the official Linux x86_64 v1.44 archive. The source-specific linker order is derived from this exact Round34 source and profile. Archived per-build inventories prove that only the target-library directory changed, while compiler and host files retained their native hashes. This is a reproducible hybrid recipe; it does not establish which original SDK or compiler built the deployed program. The five tracked TypeId constants still differ from the original. The profile restores several SDK source-path matches but does not prove original provenance or whole-program identity.

The profile has a separate dependency-cache key. Its ordinary uncached producer and fresh cached consumer agree on both ELF hashes, and consumer controls completed while the producer target was unavailable. Native-profile cache receipts remain archived as historical evidence and are not used as hybrid-profile proof. Every main crate is rebuilt; compiled main-Pump objects are excluded from the cache.

Every case's paired CPI invocation sequence is also audited, including failed transactions. One bounded queue schedules both corpora and keeps per-suite results for verified resumption; the preserved queue state records any retry history.

Four fresh main compilations reproduce both final ELF hashes: the initial combined build, repeat, maintained source and archived source. The verifier authenticates all four hybrid-profile receipts and complete native/prepared SDK inventories, the exact target-library hashes and cache context, and the current-source layout baseline. Original executable bytes are never compiler inputs.

The loader optimization retains full actual ProgramData byte equality on every load while caching immutable expected images and hashes. Its earlier controlled benchmark and corruption controls remain applicable; full-suite timings depend on the workload and concurrent jobs.

```sh
python repro/pump/main-contract-round34-20261027/verify.py
python repro/pump/main-contract-round34-20261027/reproduce.py \\
  --registry-home ~/.cargo --sdk /path/to/native-macos-v1.44 \\
  --target-library-directory /path/to/linux-v1.44/rust/lib/rustlib/sbf-solana-solana/lib \\
  --output work/reproduce-main-round34
```

The native SDK and official target libraries are explicit external inputs and are not bundled or downloaded by this archive. Their required hashes and the official archive provenance are recorded in `inputs/scripts/pump_linux_v144_sbf_libraries.json`. A reproduction rejects missing, extra or changed target libraries.

[Previous maintained checkpoint: Round33](../main-contract-round33-20261027/README.md). The remaining {total-n} function windows, validation paths, data, relocations and original build provenance are unresolved. [Parallel work queue](../../../research/main-pump-parallel-checkpoint-20261027/REMAINING-WORK.json).
'''
(P / 'README.md').write_text(text)
