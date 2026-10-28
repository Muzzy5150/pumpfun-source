#!/usr/bin/env python3
"""Synthetic signed AdminCto zero-token payout counterexamples.

Reuses the published local fixture and captured dependency programs unchanged.
The expected observations are always obtained from the immutable main ELF.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import pump_admin_cto_differential as fixture


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases():
    quote = fixture.Pubkey.from_bytes(bytes([88]) * 32)
    current = fixture.OTHER.pubkey()
    base = {"current": str(current), "current_writable": True, "quote": str(quote)}
    rows = []
    for native in [False, True]:
        for writable in [False, True]:
            for status in ["missing", "initialized", "frozen", "uninitialized", "wrong-mint", "wrong-authority", "system-owner", "pump-owner", "fees-owner"]:
                data = bytearray(165)
                data[:32] = bytes(fixture.QUOTE if native else quote)
                data[32:64] = bytes(current)
                data[64:72] = (100).to_bytes(8, "little")
                data[108] = 2 if status == "frozen" else 0 if status == "uninitialized" else 1
                if status == "wrong-mint":
                    data[:32] = bytes(fixture.MINT)
                if status == "wrong-authority":
                    data[32:64] = bytes(fixture.AUTH.pubkey())
                owner = {"system-owner": fixture.Pubkey.default(), "pump-owner": fixture.PUMP, "fees-owner": fixture.PROGRAM}.get(status, fixture.TOKEN)
                dest = {"data": "", "lamports": 0, "owner": str(fixture.Pubkey.default())} if status == "missing" else {"data": data.hex(), "lamports": 2039280, "owner": str(owner)}
                c = {**base, "name": f"{'native' if native else 'token'}-{'writable' if writable else 'readonly'}-{status}", "current_writable": writable, "accounts": {"current_creator_quote_token_account": dest}}
                if native:
                    del c["quote"]
                rows.append(c)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bound = [Path(__file__).resolve(), args.candidate.resolve()]
    bound += [ROOT / "scripts" / name for name in ["pump_admin_cto_differential.py", "fees_donation_create_differential.py", "fees_admin_differential.py", "pump_validate_admin.py", "pump_amm_admin_differential.py"]]
    bound += [ROOT / "evidence/original" / name / "deployed.so" for name in ["pump", "pump_amm", "pump_fees"]]
    bound += [ROOT / "evidence/dependencies" / name / "deployed.so" for name in ["spl_token", "spl_token_2022", "associated_token"]]
    bound += [ROOT / "evidence/upstream" / (name + ".json") for name in ["pump", "pump_amm", "pump_fees"]]
    hashes = {str(p): sha(p) for p in bound}
    rows = []
    compared = ["error", "before", "after", "events", "inner", "return"]
    for c in cases():
        original = fixture.run(c)
        candidate = fixture.run(c, args.candidate)
        differences = [field for field in compared if original[field] != candidate[field]]
        assert original["signatures_verified"] and candidate["signatures_verified"]
        rows.append({"case": c, "original": original, "candidate": candidate, "different_fields": differences})
        if differences:
            print(c["name"], differences, flush=True)
    assert hashes == {str(p): sha(p) for p in bound}, "Input changed during run"
    report = {"scope": "Signed offline AdminCto zero-token payout corpus; captured main original is the oracle. Full binary identity is not claimed.", "original_sha256": sha(ROOT / "evidence/original/pump/deployed.so"), "candidate_sha256": sha(args.candidate), "inputs_sha256": hashes, "case_count": len(rows), "compared_fields": compared, "cases": rows, "mismatches": [r["case"]["name"] for r in rows if r["different_fields"]]}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"cases": len(rows), "mismatches": len(report["mismatches"])}))
    return bool(report["mismatches"])


if __name__ == "__main__":
    raise SystemExit(main())
