"""Signed native creator-recipient rent floor boundaries; token controls stay unfiltered."""
from pathlib import Path
import argparse, base64, gzip, hashlib, json, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "work/parallel-main-loader-optimized")]
import pump_captured_loader
pump_captured_loader.install()
import pump_creator_collect_v2_differential as fixture
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction


def cases():
    for version in ["legacy", "v2"]:
        for data_len in [0, 8]:
            floor = (128 + data_len) * 3480 * 2
            for available in [0, 1, 10, 890880]:
                for recipient in sorted({0, max(0, floor - available - 1), max(0, floor - available), floor}):
                    yield {
                        "name": f"{version}/len={data_len}/available={available}/recipient={recipient}",
                        "version": version,
                        "native": 890880 + available,
                        "patch": {"creator": {"lamports": recipient, "bytes": [(0, "00" * data_len)]}},
                    }
    for token22 in [False, True]:
        for amount in [0, 1]:
            for recipient in [0, 1]:
                yield {
                    "name": f"token/token22={token22}/amount={amount}/recipient={recipient}",
                    "version": "v2",
                    "quote": str(fixture.QUOTE),
                    "token22": token22,
                    "tokens": amount,
                    "patch": {"creator": {"lamports": recipient}},
                }


def run(case, candidate=None):
    original_ix = fixture.IX
    try:
        name = "collect_creator_fee" if case["version"] == "legacy" else "collect_creator_fee_v2"
        fixture.IX = next(row for row in fixture.J["instructions"] if row["name"] == name)
        return fixture.run(case, candidate)
    finally:
        fixture.IX = original_ix


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
        a, b = run(case), run(case, args.candidate)
        assert a["transaction_base64"] == b["transaction_base64"]
        for side in [a, b]:
            assert all(VersionedTransaction.from_bytes(base64.b64decode(side["transaction_base64"])).verify_with_results())
        differences = [key for key in ["error", "before", "after", "events", "inner", "returns"] if a[key] != b[key]]
        rows.append({"case": case, "original": a, "candidate": b, "different_fields": differences})
        print(case["name"], a["error"], b["error"], differences, flush=True)
    report = {
        "scope": __doc__, "case_count": len(rows), "cases": rows,
        "candidate_sha256": hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "fixture_sha256": hashlib.sha256(Path(fixture.__file__).read_bytes()).hexdigest(),
        "mismatches": [i for i, row in enumerate(rows) if row["different_fields"]],
        "diagnostics": audit({"creator_recipient_rent": rows}),
    }
    args.output.write_bytes(gzip.compress(json.dumps(report).encode(), mtime=0))
    print({"cases": len(rows), "mismatches": len(report["mismatches"]), "diagnostic_mismatches": len(report["diagnostics"]["mismatches"])}, flush=True)


if __name__ == "__main__":
    main()
