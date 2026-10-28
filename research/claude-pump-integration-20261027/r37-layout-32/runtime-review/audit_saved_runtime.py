#!/usr/bin/env python3
"""Hermetic, read-only audit of the retained L32 signed runtime evidence."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import base64
import difflib
import gzip
import hashlib
import json
import re


class VerificationError(RuntimeError):
    """The saved evidence failed a fail-closed verification rule."""


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
ROOT = next((p for p in PACKAGE.parents if (p / "evidence/original/pump/deployed.so").is_file()), None)
if ROOT is None:
    raise VerificationError("repository root containing the captured Pump executable was not found")

PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
ORIGINAL = "7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d"
CANDIDATE = "45c5af2485f6d8138b471cbd6b56e0bf59135dcefea15f055d6387b4f1ac0bca"
RECEIPT = "1699fc200680b6bd0e36592eab2805b434cb3eb255c2e7193f6af4b8b9c67aab"
EXPECTED_CASES = 10_468
EXPECTED_SUITES = 44
EXPECTED_FAMILIES = Counter({
    "source_file_path_only": 52,
    "missing_creator_non_system_notice": 5,
    "missing_canonical_pool_notice": 3,
    "ordinary_message_order": 6,
    "missing_creator_quote_frozen_notice": 9,
})
NOTICE_FAMILIES = {
    "Program log: Creator is not a system-owned wallet; fees left in the vaults":
        "missing_creator_non_system_notice",
    "Program log: No canonical pump pool for this mint; curve only":
        "missing_canonical_pool_notice",
    "Program log: Creator quote token account is frozen; fees left in the vaults":
        "missing_creator_quote_frozen_notice",
}
COMPUTE = re.compile(r"^Program \S+ consumed \d+ of \d+ compute units$")
SOURCE = re.compile(r"((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.rs):\d+(?::\d+)?")
SOURCE_FILE = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.rs:<source>")
LOG_KEYS = {"logs", "relevant_logs"}
COMPUTE_KEYS = {"compute_units", "compute_units_consumed"}


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
    try:
        raw = path.read_bytes()
        decoded = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        return json.loads(decoded, object_pairs_hook=_unique_object)
    except VerificationError:
        raise
    except Exception as exc:
        raise VerificationError(f"cannot decode {path}: {exc}") from exc


def index_pairs(suites):
    require(isinstance(suites, dict), "suites is not an object")
    rows = {}

    def walk(value, path):
        if isinstance(value, dict):
            if isinstance(value.get("original"), dict) and isinstance(value.get("candidate"), dict):
                require(path not in rows, f"duplicate case identity: {path}")
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


def normalized_structure(value, expected_hash: str):
    """Retain all structured behavior and replace only the checked Pump executable."""
    if isinstance(value, dict):
        return {
            key: normalized_structure(child, expected_hash)
            for key, child in value.items()
            if key not in LOG_KEYS and key not in COMPUTE_KEYS
        }
    if isinstance(value, list):
        return [normalized_structure(child, expected_hash) for child in value]
    if isinstance(value, str) and value == expected_hash:
        return "<checked-pump-executable>"
    return value


def normalized_logs(lines):
    require(isinstance(lines, list) and all(isinstance(line, str) for line in lines),
            "logs must be a list of strings")
    return [SOURCE.sub(r"\1:<source>", line) for line in lines if not COMPUTE.fullmatch(line)]


def outer_pump_logs(lines):
    lines = normalized_logs(lines)
    begin = next((index for index, line in enumerate(lines)
                  if line.startswith(f"Program {PUMP} invoke [")), None)
    if begin is None:
        return None
    depth = 0
    for index in range(begin, len(lines)):
        line = lines[index]
        if line.startswith(f"Program {PUMP} invoke ["):
            depth += 1
        elif line == f"Program {PUMP} success" or line.startswith(f"Program {PUMP} failed:"):
            depth -= 1
            require(depth >= 0, "Pump invocation nesting underflow")
            if depth == 0:
                return lines[begin:index + 1]
    raise VerificationError("unterminated outer Pump invocation")


def classify_logs(original, candidate, context: str):
    if original == candidate:
        return None
    original_without_files = [SOURCE_FILE.sub("<source-file>:<source>", line) for line in original]
    candidate_without_files = [SOURCE_FILE.sub("<source-file>:<source>", line) for line in candidate]
    if original_without_files == candidate_without_files:
        return "source_file_path_only"

    operations = [op for op in difflib.SequenceMatcher(
        a=original, b=candidate, autojunk=False
    ).get_opcodes() if op[0] != "equal"]
    if len(operations) == 1:
        operation, left_start, left_end, right_start, right_end = operations[0]
        if operation == "delete" and left_end == left_start + 1 and right_start == right_end:
            family = NOTICE_FAMILIES.get(original[left_start])
            if family:
                return family
    if Counter(original) == Counter(candidate):
        return "ordinary_message_order"
    raise VerificationError(f"{context}: unclassified ordered-log difference")


def _transaction_type():
    try:
        from solders.transaction import VersionedTransaction
    except Exception as exc:
        raise VerificationError("pinned dependency solders is required for signature verification") from exc
    return VersionedTransaction


def verify_transaction(encoded: str, context: str, transaction_type=None):
    transaction_type = transaction_type or _transaction_type()
    try:
        raw = base64.b64decode(encoded, validate=True)
        transaction = transaction_type.from_bytes(raw)
        checks = transaction.verify_with_results()
    except Exception as exc:
        raise VerificationError(f"{context}: invalid serialized transaction: {exc}") from exc
    require(checks and all(checks), f"{context}: signature verification failed")
    require(bytes(transaction) == raw, f"{context}: transaction decode is not byte-stable")
    return hashlib.sha256(raw).hexdigest()


def transactions(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if key == "transaction_base64":
                require(isinstance(child, str), f"{child_path}: transaction is not base64 text")
                yield child_path, child
            else:
                yield from transactions(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from transactions(child, f"{path}/{index}")


def program_hashes(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if key in ("executed_program_sha256", "candidate_sha256", "original_sha256"):
                yield child_path, child
            elif key == "program_sha256" and isinstance(child, dict) and PUMP in child:
                yield f"{child_path}/{PUMP}", child[PUMP]
            yield from program_hashes(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from program_hashes(child, f"{path}/{index}")


def audit(document, transaction_type=None):
    require(document.get("original_sha256") == ORIGINAL, "receipt original digest changed")
    require(document.get("candidate_sha256") == CANDIDATE, "receipt candidate digest changed")
    require(document.get("case_count") == EXPECTED_CASES, "receipt case count changed")
    suites = document.get("suites")
    require(isinstance(suites, dict) and len(suites) == EXPECTED_SUITES, "receipt suite count changed")
    require(not document.get("mismatches"), "recorded mismatch list is nonempty")
    require(not document.get("diagnostics", {}).get("mismatches"), "diagnostic mismatch list is nonempty")
    rows = index_pairs(suites)
    require(len(rows) == EXPECTED_CASES, f"paired case census is {len(rows)}")

    counts = Counter()
    families = Counter()
    distinct = set()
    top_level = set()
    nested = []
    transaction_type = transaction_type or _transaction_type()
    for path, row in rows.items():
        original = row["original"]
        candidate = row["candidate"]
        require(normalized_structure(original, ORIGINAL) == normalized_structure(candidate, CANDIDATE),
                f"{path}: structured behavior differs")

        for side, outcome, expected in (
            ("original", original, ORIGINAL), ("candidate", candidate, CANDIDATE),
        ):
            seen_hash = False
            for hash_path, digest in program_hashes(outcome):
                if digest in (ORIGINAL, CANDIDATE):
                    require(digest == expected, f"{path}/{side}{hash_path}: executable identity swapped")
                    seen_hash = True
            if seen_hash:
                counts["outcomes_with_checked_program_hash"] += 1

            for tx_path, encoded in transactions(outcome):
                digest = verify_transaction(encoded, f"{path}/{side}{tx_path}", transaction_type)
                counts["signed_transaction_occurrences_reverified"] += 1
                distinct.add(digest)
                if tx_path == "/transaction_base64":
                    top_level.add(digest)
                    counts["top_level_signed_transaction_occurrences"] += 1
                else:
                    nested.append({"case": path, "side": side, "field": tx_path, "sha256": digest})

        left = outer_pump_logs(original.get("logs", []))
        right = outer_pump_logs(candidate.get("logs", []))
        if left is None and right is None:
            counts["neither_invokes_main"] += 1
        else:
            require(left is not None and right is not None, f"{path}: only one outcome invokes Pump")
            counts["main_log_pairs"] += 1
            family = classify_logs(left, right, path)
            if family is None:
                counts["equal_main_sequences"] += 1
            else:
                families[family] += 1

    require(counts["signed_transaction_occurrences_reverified"] == 18_284,
            "recursive signed transaction occurrence count changed")
    require(len(distinct) == 2_409, "recursive distinct transaction count changed")
    require(counts["top_level_signed_transaction_occurrences"] == 18_268,
            "top-level signed transaction occurrence count changed")
    require(len(top_level) == 2_407, "top-level distinct transaction count changed")
    require(len(nested) == 16 and len({row["sha256"] for row in nested}) == 2,
            "nested bootstrap transaction scope changed")
    require(counts["main_log_pairs"] == 10_456,
            f"main invocation pair count changed: {counts['main_log_pairs']}")
    require(families == EXPECTED_FAMILIES, f"ordered-log family census changed: {dict(families)}")
    require(sum(value for key, value in families.items() if key != "source_file_path_only") == 23,
            "non-filename residual log count changed")

    return {
        "verified": True,
        # Compatibility fields retained for the independent L32 packet verifier.
        "counts": {"pairs": EXPECTED_CASES},
        "state_differences": [],
        "scope": "retained offline receipts; no VM replay or live-chain access",
        "suites": EXPECTED_SUITES,
        "cases": EXPECTED_CASES,
        "signed_transaction_occurrences_reverified": 18_284,
        "distinct_signed_transactions": 2_409,
        "top_level_transaction_occurrences": 18_268,
        "top_level_distinct_transactions": 2_407,
        "nested_bootstrap_transactions": nested,
        "ordered_log_families": dict(sorted(families.items())),
        "non_filename_log_differences": 23,
        "filename_only_log_differences": 52,
        "structured_mismatches": 0,
        "normalization": [
            "exact compute-unit scalar fields and consumption lines excluded",
            "source line and column coordinates normalized; filenames preserved",
            "checked original/candidate Pump executable substitution only",
        ],
        "original_sha256": ORIGINAL,
        "candidate_sha256": CANDIDATE,
        "full_receipt_sha256": RECEIPT,
    }


def verify():
    receipt = PACKAGE / "full.json.gz"
    require(sha256(ROOT / "evidence/original/pump/deployed.so") == ORIGINAL,
            "captured original executable digest changed")
    require(sha256(PACKAGE / "candidate.so") == CANDIDATE, "packaged candidate digest changed")
    require(sha256(receipt) == RECEIPT, "retained full receipt digest changed")
    return audit(read_document(receipt))


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
