"""Signed supply-selection and market-cap divisor boundaries; captured dependencies."""
import argparse, gzip, hashlib, importlib, json, multiprocessing, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

def init():
    import pump_captured_loader as loader
    loader.install()

def cases():
    routes = [("pump_legacy_buy_differential", "buy", False),
              ("pump_legacy_buy_differential", "buy_exact_sol_in", False),
              ("pump_legacy_sell_differential", "sell", False)]
    routes += [("pump_buy_v2_differential" if "buy" in kind else "pump_sell_v2_differential", kind, token)
               for kind in ["buy_v2", "buy_exact_quote_in_v2", "sell_v2"] for token in [False, True]]
    pairs = [(0, 10**15), (1, 10**15), (10**15, 0), (10**15, 1), (2**64-1, 10**15), (10**15, 2**64-1)]
    out = []
    for module, kind, token in routes:
        for mayhem in [False, True]:
            for mint_supply, curve_supply in pairs:
                c = {"name": f"supply_{kind}_{token}_{mayhem}_{mint_supply}_{curve_supply}",
                     "kind": kind, "token_quote": token, "amount": 500000000,
                     "minimum": 1 if "exact" in kind else 0 if "sell" in kind else 10**12,
                     "reserved": mayhem, "curve_bytes": [[81, int(mayhem)]],
                     "account_mutations": {
                         "base_mint" if kind.endswith("_v2") else "mint": {"u64": [[36, mint_supply]]},
                         "bonding_curve": {"u64": [[40, curve_supply]]}}}
                out.append((module, c))
            if kind != "buy_v2":
                for divisor in [0, 1, 2**32, 2**64-1]:
                    c = {"name": f"divisor_{kind}_{token}_{mayhem}_{divisor}",
                         "kind": kind, "token_quote": token, "amount": 500000000,
                         "minimum": 1 if "exact" in kind else 0 if "sell" in kind else 10**12,
                         "reserved": mayhem, "curve_bytes": [[81, int(mayhem)]],
                         "account_mutations": {"bonding_curve": {"u64": [[8, divisor]]}}}
                    out.append((module, c))
    return out

def execute(item):
    name, case, candidate = item
    import pump_captured_loader as loader
    module = importlib.import_module(name)
    begin = len(loader.LOADS)
    original = module.run(case)
    actual = module.run(case, Path(candidate))
    loads = loader.LOADS[begin:]
    assert len(loads) == 2
    fields = [k for k in ["error", "accounts", "events", "inner", "return_data"] if original[k] != actual[k]]
    return {"case": case, "original": original, "candidate": actual,
            "different_fields": fields, "loader": loads}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(); init(); rows = []
    with multiprocessing.get_context("spawn").Pool(4, initializer=init) as pool:
        for row in pool.imap(execute, [(n,c,str(a.candidate.resolve())) for n,c in cases()]):
            rows.append(row)
            if row["different_fields"]:
                print(json.dumps({"case": row["case"]["name"], "fields": row["different_fields"],
                                  "original": row["original"]["error"], "candidate": row["candidate"]["error"]}), flush=True)
    from pump_diagnostic_audit import audit
    diagnostics = audit({"market_cap": rows})
    paths = [Path(__file__), ROOT/"scripts/pump_captured_loader.py", ROOT/"scripts/pump_trade_fixture.py"]
    paths += [ROOT/"scripts"/(m+".py") for m in sorted({m for m,c in cases()})]
    result = {"case_count":len(rows), "suites":{"market_cap": rows}, "diagnostics":diagnostics,
              "mismatches":[i for i,r in enumerate(rows) if r["different_fields"]],
              "candidate_sha256":hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
              "source_sha256":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    a.output.write_bytes(gzip.compress(json.dumps(result).encode(), mtime=0))
    print(json.dumps({"cases":len(rows), "mismatches":len(result["mismatches"]),
                      "strict_cases":diagnostics["log_bearing_cases"], "strict_mismatches":len(diagnostics["mismatches"])}), flush=True)
    return bool(result["mismatches"] or diagnostics["mismatches"])

if __name__ == "__main__":
    raise SystemExit(main())
