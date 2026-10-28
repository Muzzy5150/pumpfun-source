#!/usr/bin/env python3
"""Fail closed on any unapproved L31-to-L32 runtime transition."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import gzip
import hashlib
import json
import re


class VerificationError(RuntimeError):
    """The retained evidence does not satisfy the sealed transition contract."""


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
ROOT = next((p for p in PACKAGE.parents if (p / "evidence/original/pump/deployed.so").is_file()), None)
if ROOT is None:
    raise VerificationError("repository root containing the captured Pump executable was not found")

L31 = ROOT / "research/claude-pump-integration-20261027/r37-layout-31"
L32 = PACKAGE
ORIGINAL = "7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d"
L31_CANDIDATE = "85e7a54ee09f1074275fa92da82cc2ed879371c395ef73c703745a1bd77c7ef1"
L32_CANDIDATE = "45c5af2485f6d8138b471cbd6b56e0bf59135dcefea15f055d6387b4f1ac0bca"
L31_RECEIPT = "84b804bc9294625b65d83d9b1b215182f48d8ff28d442b707ea2582a3551b969"
L32_RECEIPT = "1699fc200680b6bd0e36592eab2805b434cb3eb255c2e7193f6af4b8b9c67aab"
EXPECTED_SUITES = 44
EXPECTED_CASES = 10_468
EXPECTED_UNCHANGED = 10_353
EXPECTED_INSERTIONS = Counter({
    "Program log: Nothing to sweep for fee bucket 0": 43,
    "Program log: Nothing to sweep for fee bucket 1": 41,
    "Program log: No cashback to claim": 31,
})
COMPUTE = re.compile(r"^Program \S+ consumed \d+ of \d+ compute units$")
COMPUTE_KEYS = {"compute_units", "compute_units_consumed"}
LOG_KEYS = {"logs", "relevant_logs"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing, non-regular, or linked input: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def read_document(path: Path):
    require(path.is_file() and not path.is_symlink(), f"missing, non-regular, or linked receipt: {path}")
    raw = path.read_bytes()
    try:
        decoded = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        return json.loads(decoded, object_pairs_hook=_unique_object)
    except VerificationError:
        raise
    except Exception as exc:
        raise VerificationError(f"cannot decode {path}: {exc}") from exc


def normalized_logs(lines, context: str):
    require(isinstance(lines, list) and all(isinstance(line, str) for line in lines),
            f"{context}: log field is not a string list")
    return [line for line in lines if not COMPUTE.fullmatch(line)]


def log_fields(value, path=""):
    found = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if key in LOG_KEYS:
                require(child_path not in found, f"duplicate log identity: {child_path}")
                found[child_path] = normalized_logs(child, child_path)
            else:
                nested = log_fields(child, child_path)
                require(not (set(found) & set(nested)), f"duplicate nested log identity below {child_path}")
                found.update(nested)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            nested = log_fields(child, f"{path}/{index}")
            require(not (set(found) & set(nested)), f"duplicate nested log identity below {path}/{index}")
            found.update(nested)
    return found


def structured(value, hash_map=None):
    """Keep every outcome field except logs and explicitly unstable compute totals."""
    hash_map = hash_map or {}
    if isinstance(value, dict):
        return {
            key: structured(child, hash_map)
            for key, child in value.items()
            if key not in LOG_KEYS and key not in COMPUTE_KEYS
        }
    if isinstance(value, list):
        return [structured(child, hash_map) for child in value]
    if isinstance(value, str):
        return hash_map.get(value, value)
    return value


def require_equal(left, right, context: str) -> None:
    require(left == right, f"{context}: values differ")


def index_pairs(suites, label: str):
    require(isinstance(suites, dict), f"{label}: suites is not an object")
    rows = {}

    def walk(value, path):
        if isinstance(value, dict):
            if isinstance(value.get("original"), dict) and isinstance(value.get("candidate"), dict):
                require(path not in rows, f"{label}: duplicate case identity {path}")
                rows[path] = value
                return
            for key, child in value.items():
                walk(child, f"{path}/{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}/{index}")

    for suite, value in suites.items():
        walk(value, suite)
    return rows


def inserted_message(old, new, context: str):
    if old == new:
        return None
    require(len(new) == len(old) + 1, f"{context}: transition is not a single insertion")
    positions = [index for index in range(len(new)) if new[:index] + new[index + 1:] == old]
    require(len(positions) == 1, f"{context}: insertion position is ambiguous or changes ordering")
    message = new[positions[0]]
    require(message in EXPECTED_INSERTIONS, f"{context}: unexpected inserted message {message!r}")
    return message


def verify_documents(l31, l32):
    for label, document, candidate in (
        ("L31", l31, L31_CANDIDATE), ("L32", l32, L32_CANDIDATE),
    ):
        require(document.get("original_sha256") == ORIGINAL, f"{label}: original digest changed")
        require(document.get("candidate_sha256") == candidate, f"{label}: candidate digest changed")
        require(document.get("case_count") == EXPECTED_CASES, f"{label}: case count changed")
        require(isinstance(document.get("suites"), dict) and len(document["suites"]) == EXPECTED_SUITES,
                f"{label}: suite count changed")
        require(not document.get("mismatches"), f"{label}: recorded mismatches are nonempty")
        require(not document.get("diagnostics", {}).get("mismatches"),
                f"{label}: recorded diagnostic mismatches are nonempty")

    require_equal(set(l31["suites"]), set(l32["suites"]), "suite identities")
    old_rows = index_pairs(l31["suites"], "L31")
    new_rows = index_pairs(l32["suites"], "L32")
    require(len(old_rows) == len(new_rows) == EXPECTED_CASES, "paired case census changed")
    require_equal(set(old_rows), set(new_rows), "case identities")

    insertions = Counter()
    changed_paths = []
    unchanged = 0
    for path, old in old_rows.items():
        new = new_rows[path]
        for identity in ("case", "parameters"):
            if identity in old or identity in new:
                require_equal(old.get(identity), new.get(identity), f"{path}: {identity} identity")

        require_equal(structured(old["original"]), structured(new["original"]),
                      f"{path}: original structured outcome")
        require_equal(
            structured(old["candidate"], {L31_CANDIDATE: "<candidate>"}),
            structured(new["candidate"], {L32_CANDIDATE: "<candidate>"}),
            f"{path}: candidate structured transition",
        )
        require_equal(
            structured(new["original"], {ORIGINAL: "<pump-program>"}),
            structured(new["candidate"], {L32_CANDIDATE: "<pump-program>"}),
            f"{path}: original/candidate structured outcome",
        )

        original_old = log_fields(old["original"])
        original_new = log_fields(new["original"])
        require_equal(original_old, original_new, f"{path}: original ordered logs")
        candidate_old = log_fields(old["candidate"])
        candidate_new = log_fields(new["candidate"])
        require_equal(list(candidate_old), list(candidate_new), f"{path}: candidate log-field identities")
        message = inserted_message(candidate_old.get("/logs", []), candidate_new.get("/logs", []), path)
        for log_path in candidate_old:
            if log_path != "/logs":
                nested_message = inserted_message(
                    candidate_old[log_path], candidate_new[log_path], f"{path}{log_path}"
                )
                require(nested_message in (None, message),
                        f"{path}{log_path}: nested log insertion disagrees with the primary sequence")
        if message is None:
            unchanged += 1
        else:
            insertions[message] += 1
            changed_paths.append({"path": path, "message": message})

    require(unchanged == EXPECTED_UNCHANGED, f"unchanged candidate sequence count is {unchanged}")
    require(len(changed_paths) == sum(EXPECTED_INSERTIONS.values()),
            f"insertion-only sequence count is {len(changed_paths)}")
    require_equal(insertions, EXPECTED_INSERTIONS, "diagnostic insertion census")
    return {
        "verified": True,
        "suites": EXPECTED_SUITES,
        "cases": EXPECTED_CASES,
        "original_log_sequences_changed": 0,
        "candidate_log_sequences_unchanged": unchanged,
        "candidate_log_sequences_insertion_only": len(changed_paths),
        "inserted_lines": dict(sorted(insertions.items())),
        "structured_transitions_changed": 0,
        "changed_paths": changed_paths,
        "normalization": ["exact compute-consumption lines and compute-unit scalar fields only"],
    }


def verify():
    require(sha256(ROOT / "evidence/original/pump/deployed.so") == ORIGINAL,
            "captured original executable digest changed")
    require(sha256(L31 / "candidate.so") == L31_CANDIDATE, "L31 candidate digest changed")
    require(sha256(L32 / "candidate.so") == L32_CANDIDATE, "L32 candidate digest changed")
    l31_receipt = L31 / "full.json.gz"
    l32_receipt = L32 / "full.json.gz"
    require(sha256(l31_receipt) == L31_RECEIPT, "L31 retained receipt digest changed")
    require(sha256(l32_receipt) == L32_RECEIPT, "L32 fresh receipt digest changed")
    return verify_documents(read_document(l31_receipt), read_document(l32_receipt))


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
