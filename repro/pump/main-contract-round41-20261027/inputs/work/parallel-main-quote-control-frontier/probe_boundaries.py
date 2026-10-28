"""Signed QuoteControl capacity and competing mint-validation boundaries."""
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
import pump_quote_control_fresh_differential as fixture
from pump_diagnostic_audit import audit
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction


def cases():
    keys = {
        "fresh": fixture.MINT_C,
        "duplicate": fixture.MINT_A,
        "zero": Pubkey.default(),
        "native": Pubkey.from_string("So11111111111111111111111111111111111111112"),
        "native2022": Pubkey.from_string("9pan9bMn5HatX4EJdBwg9VgCa7Uz5HL8N1m5D3NdXejP"),
        "pump": Pubkey.from_string("pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"),
    }
    for count in [255, 256, 257]:
        entries = [(fixture.MINT_A, 1)] + [
            (Pubkey(hashlib.sha256(f"quote-control-boundary-{i}".encode()).digest()), i)
            for i in range(1, count)
        ]
        for kind, key in keys.items():
            for role in ["authority", "admin"]:
                yield {
                    "name": f"add/{count}/{kind}/{role}",
                    "count": count,
                    "mint_kind": kind,
                    "role": role,
                }, {
                    "args": bytes(key) + fixture.u64(123),
                    "roles": role,
                    "state": fixture.qc_account(
                        admin=fixture.ADMIN.pubkey(),
                        reserves_admin=fixture.RESERVES_ADMIN.pubkey(),
                        mints=entries,
                    ),
                }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    rows = []
    original = ROOT / "evidence/original/pump/deployed.so"
    for case, kwargs in cases():
        a = fixture.execute(original, "add_quote_control_mint", **kwargs)
        b = fixture.execute(args.candidate, "add_quote_control_mint", **kwargs)
        assert a["transaction_base64"] == b["transaction_base64"]
        for result in [a, b]:
            assert all(VersionedTransaction.from_bytes(base64.b64decode(result["transaction_base64"])).verify_with_results())
        differences = [key for key in ["error", "before_accounts", "after_accounts", "event_payloads", "inner_instructions", "return_data"] if a[key] != b[key]]
        rows.append({"case": case, "original": a, "candidate": b, "different_fields": differences})
        print(case["name"], a["error"], b["error"], differences, flush=True)
    report = {
        "scope": __doc__,
        "case_count": len(rows),
        "cases": rows,
        "candidate_sha256": hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "fixture_sha256": hashlib.sha256(Path(fixture.__file__).read_bytes()).hexdigest(),
        "mismatches": [i for i, row in enumerate(rows) if row["different_fields"]],
        "diagnostics": audit({"quote_control_boundaries": rows}),
    }
    args.output.write_bytes(gzip.compress(json.dumps(report).encode(), mtime=0))
    print({"case_count": report["case_count"], "mismatches": report["mismatches"], "diagnostic_mismatches": report["diagnostics"]["mismatches"]}, flush=True)
    assert not report["mismatches"] and not report["diagnostics"]["mismatches"]


if __name__ == "__main__":
    main()
