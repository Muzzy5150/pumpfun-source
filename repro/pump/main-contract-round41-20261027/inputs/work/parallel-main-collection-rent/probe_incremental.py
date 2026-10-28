"""Deduplicated original-backed creator-collection rent and precedence cases."""
from pathlib import Path
import argparse, base64, gzip, hashlib, importlib.util, json, re, sys
ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "work/parallel-main-loader-optimized")]
import pump_captured_loader
pump_captured_loader.install()
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    definitions = json.loads((P / "combined-incremental-cases.json").read_text())["groups"]
    scripts = {
        "primary": P / "probe_rent.py",
        "precedence": ROOT / "work/parallel-main-collection-rent-review/probe-precedence.py",
        "executable": ROOT / "work/parallel-main-collection-rent-review/probe-executable.py",
        "owner-live": ROOT / "work/parallel-main-collection-rent-review/probe-owner-live.py",
    }
    rows = []
    for group, path in scripts.items():
        module = load(path, "incremental_collection_" + group.replace("-", "_"))
        host = module if hasattr(module, "run") else module.base
        generate = module.cases if hasattr(module, "cases") else module.base.cases
        available = {case["name"]: case for case in generate()}
        for definition in definitions[group]:
            case = available[definition["name"]]
            a, b = host.run(case), host.run(case, args.candidate)
            identity = hashlib.sha256((a["transaction_base64"] + json.dumps({k:v for k,v in a["before"].items() if v is not None}, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()
            assert identity == definition["input_hash"]
            assert a["transaction_base64"] == b["transaction_base64"]
            for side in [a, b]:
                assert all(VersionedTransaction.from_bytes(base64.b64decode(side["transaction_base64"])).verify_with_results())
            differences = [k for k in ["error", "before", "after", "events", "inner", "returns"] if a[k] != b[k]]
            messages = lambda r: [line for line in r["logs"] if line.startswith("Program log:") and "AnchorError" not in line]
            if messages(a) != messages(b):
                differences.append("plain_messages")
            sequence = lambda r: [line for line in r["logs"] if re.match(r"^Program [1-9A-HJ-NP-Za-km-z]+ (?:invoke \[|success$|failed:)", line)]
            if sequence(a) != sequence(b):
                differences.append("invocations")
            rows.append({"case": {"group": group, **case}, "original": a, "candidate": b, "different_fields": differences, "input_hash": identity})
            print(group, case["name"], differences, flush=True)
    report = {
        "scope": __doc__, "case_count": len(rows), "cases": rows,
        "candidate_sha256": hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        "mismatches": [i for i,r in enumerate(rows) if r["different_fields"]],
        "diagnostics": audit({"collection_rent_incremental": rows}),
    }
    args.output.write_bytes(gzip.compress(json.dumps(report).encode(), mtime=0))
    print({"cases": len(rows), "mismatches": len(report["mismatches"]), "diagnostic_mismatches": len(report["diagnostics"]["mismatches"])}, flush=True)
    assert len(rows) == sum(len(v) for v in definitions.values())
    assert not report["mismatches"] and not report["diagnostics"]["mismatches"]


if __name__ == "__main__":
    main()
