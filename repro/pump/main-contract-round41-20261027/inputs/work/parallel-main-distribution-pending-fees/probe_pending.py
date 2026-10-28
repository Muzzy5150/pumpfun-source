"""Signed pending-creator-fee admission and precedence in main Pump distributions."""
from pathlib import Path
import argparse
import base64
import gzip
import hashlib
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "work/parallel-main-loader-optimized")]
import pump_captured_loader
pump_captured_loader.install()
import pump_creator_distribution_differential as fixture
from pump_diagnostic_audit import audit
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction


def cases():
    for route in ["native-v1", "native-v2", "token-v2"]:
        for pending in [0, 1, 2**64 - 1]:
            for status in [0, 1]:
                for available in [0, 1_000_000]:
                    for missing in [False, True]:
                        c = {
                            "name": f"{route}/pending={pending}/status={status}/available={available}/missing={missing}",
                            "op": "distribute_creator_fees" if route == "native-v1" else "distribute_creator_fees_v2",
                            "status": status,
                            "pump_sol": available,
                            "direct_mutations": {"curve": {"patches": [(125, pending.to_bytes(8, "little").hex())]}},
                        }
                        if route == "token-v2":
                            quote = Pubkey.from_bytes(bytes([88]) * 32)
                            c.update(quote=str(quote), curve_patches=[(83, bytes(quote).hex())], remaining_atas=True, grouped_remaining=True, pump_tokens=available)
                        if missing:
                            c["remaining"] = []
                        yield c


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cases-file", type=Path)
    args = p.parse_args()
    selected = set(json.loads(args.cases_file.read_text())["names"]) if args.cases_file else None
    rows = []
    for case in cases():
        if selected is not None and case["name"] not in selected:
            continue
        a = fixture.run(case)
        b = fixture.run(case, args.candidate)
        assert a["transaction_base64"] == b["transaction_base64"]
        for side in [a, b]:
            assert all(VersionedTransaction.from_bytes(base64.b64decode(side["transaction_base64"])).verify_with_results())
        differences = [k for k in ["error", "before", "after", "events", "inner", "return"] if a[k] != b[k]]
        rows.append({"case": case, "original": a, "candidate": b, "different_fields": differences})
        print(case["name"], a["error"], b["error"], differences, flush=True)
    report = {
        "scope": __doc__, "case_count": len(rows), "cases": rows,
        "candidate_sha256": hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "fixture_sha256": hashlib.sha256(Path(fixture.__file__).read_bytes()).hexdigest(),
        "mismatches": [i for i, row in enumerate(rows) if row["different_fields"]],
        "diagnostics": audit({"pending_creator_fee_admission": rows}),
    }
    args.output.write_bytes(gzip.compress(json.dumps(report).encode(), mtime=0))
    print({"case_count": report["case_count"], "mismatches": report["mismatches"], "diagnostic_mismatches": report["diagnostics"]["mismatches"]}, flush=True)


if __name__ == "__main__":
    main()
