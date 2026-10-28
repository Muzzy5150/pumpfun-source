#!/usr/bin/env python3
"""Negative controls for the hermetic saved-runtime audit."""
from pathlib import Path
from unittest import mock
import base64
import importlib.util
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("audit_saved_runtime", HERE / "audit_saved_runtime.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from solders.hash import Hash
        from solders.keypair import Keypair
        from solders.message import Message
        from solders.system_program import TransferParams, transfer
        from solders.transaction import Transaction

        signer = Keypair()
        instruction = transfer(TransferParams(
            from_pubkey=signer.pubkey(), to_pubkey=Keypair().pubkey(), lamports=1,
        ))
        cls.encoded = base64.b64encode(bytes(Transaction(
            [signer], Message([instruction], signer.pubkey()), Hash.default(),
        ))).decode()

    def test_valid_signature_is_accepted(self):
        self.assertEqual(len(audit.verify_transaction(self.encoded, "valid")), 64)

    def test_mutated_signature_is_rejected(self):
        raw = bytearray(base64.b64decode(self.encoded))
        raw[1] ^= 1
        with self.assertRaises(audit.VerificationError):
            audit.verify_transaction(base64.b64encode(raw).decode(), "mutated")

    def test_changed_executable_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "candidate.so"
            artifact.write_bytes(b"changed")
            with self.assertRaises(audit.VerificationError):
                audit.require(audit.sha256(artifact) == audit.CANDIDATE, "candidate hash changed")

    def test_swapped_executable_identity_is_rejected(self):
        original = {"executed_program_sha256": audit.CANDIDATE, "after": {"lamports": 1}}
        candidate = {"executed_program_sha256": audit.ORIGINAL, "after": {"lamports": 1}}
        self.assertNotEqual(
            audit.normalized_structure(original, audit.ORIGINAL),
            audit.normalized_structure(candidate, audit.CANDIDATE),
        )

    def test_modified_outcome_is_rejected(self):
        original = {"after": {"lamports": 1}, "error": None}
        candidate = {"after": {"lamports": 2}, "error": None}
        self.assertNotEqual(
            audit.normalized_structure(original, audit.ORIGINAL),
            audit.normalized_structure(candidate, audit.CANDIDATE),
        )

    def test_missing_receipt_is_rejected(self):
        with self.assertRaises(audit.VerificationError):
            audit.read_document(HERE / "missing-receipt.json.gz")

    def test_altered_log_is_rejected(self):
        with self.assertRaises(audit.VerificationError):
            audit.classify_logs(["Program log: retained"], ["Program log: altered"], "case")

    def test_reordered_message_is_classified_separately(self):
        self.assertEqual(
            audit.classify_logs(["a", "b"], ["b", "a"], "case"),
            "ordinary_message_order",
        )

    def test_duplicate_json_case_key_is_rejected(self):
        with self.assertRaises(audit.VerificationError):
            audit._unique_object([("cases", []), ("cases", [])])

    def test_missing_dependency_is_rejected(self):
        real_import = __import__

        def blocked(name, *args, **kwargs):
            if name.startswith("solders"):
                raise ModuleNotFoundError(name)
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=blocked):
            with self.assertRaises(audit.VerificationError):
                audit._transaction_type()

    def test_source_filename_difference_is_not_erased_from_classification(self):
        left = ["Program log: panicked at programs/pump/src/a.rs:<source>: failure"]
        right = ["Program log: panicked at programs/pump/src/b.rs:<source>: failure"]
        self.assertEqual(audit.classify_logs(left, right, "case"), "source_file_path_only")


if __name__ == "__main__":
    unittest.main(verbosity=2)
