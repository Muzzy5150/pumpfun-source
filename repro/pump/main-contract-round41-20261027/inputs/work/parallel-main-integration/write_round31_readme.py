"""Write the evidence-bounded Round31 checkpoint description."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'repro/pump/main-contract-round31-20261027'
cp = json.loads((P / 'CHECKPOINT.json').read_text())
n, total = cp['normalized_windows'], cp['original_windows']
matched, size = cp['matched_text_bytes'], cp['original_text_bytes']
logs = cp['full_log_cases'] + cp['additional_log_cases']
text = f'''# Main Pump verified checkpoint — Round31

The maintained main contract matches **{n:,} / {total:,} original function windows ({100*n/total:.1f}%)**, including **{cp['raw_windows']} raw byte-equal bodies**. Those windows cover **{matched:,} / {size:,} original text bytes ({100*matched/size:.1f}%)**. The closed direct-call subset contains {cp['closed_call_windows_without_data']} windows and excludes data references. Normalization masks specified call/address operands; it does not establish referenced data or whole-program identity. **Whole-ELF identity remains false.** These figures measure binary coverage, not the fraction of engineering work completed.

The captured-loader regression passes **{cp['full_suites']} suites / {cp['full_cases']:,} cases** and **{cp['additional_suites']} focused suites / {cp['additional_cases']:,} executions**, with **{logs:,} matching paired diagnostic-log cases**. These corpora overlap. Diagnostics exclude source coordinates and compute usage. Tests use captured upgradeable-loader dimensions in local VMs. The verifier requires serialized transaction bytes for every original/candidate result and rechecks signatures and instruction attribution. No current-chain acceptance is implied.

This checkpoint recovers shared ATA admission behavior and the user-to-curve quote-payment boundaries. It restores selected token-program owner checks and ordered diagnostic operands, fixing 72 observed differences across 92 new cases. A further 56 cases confirm that this shared helper does not impose an extra token-authority check. Existing user-token authority checks remain in their callers.

Two real quote-payment bodies now match normalized original code, with all immediate internal callees accounted for. Four original windows match because each body has an additional normalized-identical original variant; the distinct caller/callee ABI of those alias windows is not independently established by this increment. The helpers now live in the original lib.rs physical file, while natural line/column differences remain unresolved.

The entrypoint2.2.1 graph and its independently qualified cache are unchanged. The source-specific linker order is rederived, and the complete corpus adds 148 signed cases.

Every case's paired CPI invocation sequence is also audited, including failed transactions. One bounded queue schedules both corpora and keeps per-suite results for verified resumption; the preserved queue state records any retry history.

The changed dependency graph was rebuilt with no cached artifacts through an ordinary physical-wrapper producer, then reproduced by a separately fresh cache consumer. Both matched hashes are retained, and the producer target was absent during independent consumer checks. Only verified external dependencies are reused; each main contract is freshly compiled.

Four independent fresh main compilations reproduce both final ELF hashes: the initial combined build, repeat, maintained source and archived source. No compiled main-Pump object is cached. Original executable bytes are never compiler inputs.

The loader optimization retains full actual ProgramData byte equality on every load while caching immutable expected images and hashes. Its earlier controlled benchmark and corruption controls remain applicable; full-suite timings depend on the workload and concurrent jobs.

```sh
python repro/pump/main-contract-round31-20261027/verify.py
python repro/pump/main-contract-round31-20261027/reproduce.py --registry-home ~/.cargo --output work/reproduce-main-round31
```

[Previous maintained checkpoint: Round30](../main-contract-round30-20261027/README.md). The remaining {total-n} function windows, validation paths, data, relocations and original build provenance are unresolved. [Parallel work queue](../../../research/main-pump-parallel-checkpoint-20261027/REMAINING-WORK.json).
'''
(P / 'README.md').write_text(text)
