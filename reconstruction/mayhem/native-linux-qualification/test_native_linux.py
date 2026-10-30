#!/usr/bin/env python3
"""Fast admission/tamper controls for the native Linux exact-build driver."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location("mayhem_native_linux", HERE / "build_linux.py")
native = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(native)


class NativeLinuxQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mayhem-native-linux-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_wrong_toolchain_archive_is_rejected(self):
        archive = self.root / "platform-tools.tar.bz2"
        archive.write_bytes(b"not the authenticated platform-tools archive")
        with self.assertRaisesRegex(ValueError, "archive digest differs"):
            native.unpack_sdk(archive, self.root / "sdk")
        self.assertFalse((self.root / "sdk").exists())

    def test_missing_and_modified_vendor_inputs_are_rejected(self):
        controller = self.root / "controller"
        controller.mkdir()
        package = self.root / "vendor/example-1.0.0"
        package.mkdir(parents=True)
        source = package / "src/lib.rs"
        source.parent.mkdir()
        source.write_bytes(b"pub fn answer() -> u8 { 42 }\n")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        checksum = {"package": "a" * 64, "files": {"src/lib.rs": digest}}
        (package / ".cargo-checksum.json").write_text(json.dumps(checksum))
        records = {"packages": [{"directory": "example-1.0.0", "package_sha256": "a" * 64, "file_count": 1}]}
        (controller / "vendor-inputs.json").write_text(json.dumps(records))

        self.assertEqual(native.check_vendor(self.root / "vendor", controller), 1)
        source.unlink()
        with self.assertRaisesRegex(ValueError, "vendor file set differs"):
            native.check_vendor(self.root / "vendor", controller)
        source.write_bytes(b"pub fn answer() -> u8 { 41 }\n")
        with self.assertRaisesRegex(ValueError, "vendor byte differs"):
            native.check_vendor(self.root / "vendor", controller)

    def test_recipe_and_canonical_source_mutations_are_rejected(self):
        recipe = self.root / "recipe"
        recipe.mkdir()
        linker = recipe / "ordered-native.ld"
        linker.write_bytes(b"SECTIONS {}\n")
        sealed = native.snapshot(recipe)
        linker.write_bytes(b"SECTIONS { .text : {} }\n")
        with self.assertRaisesRegex(ValueError, "staged recipe changed during build"):
            native.pin_snapshot(recipe, sealed, "staged recipe")

        source = self.root / "repo/programs/mayhem/src/lib.rs"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"pub fn original() {}\n")
        expected = {"src/lib.rs": native.sha256(source)}
        native.pin_canonical_sources(self.root / "repo", expected)
        source.write_bytes(b"pub fn changed() {}\n")
        with self.assertRaisesRegex(ValueError, "canonical Mayhem source changed during build"):
            native.pin_canonical_sources(self.root / "repo", expected)

    def test_existing_output_is_preserved_and_invalid_hosts_fail_closed(self):
        output = self.root / "existing"
        output.mkdir()
        marker = output / "prior-result.json"
        marker.write_bytes(b"prior result\n")
        args = types.SimpleNamespace(repo=ROOT, vendor=self.root, output=output)
        with mock.patch.object(native.platform, "system", return_value="Linux"), mock.patch.object(
            native.platform, "machine", return_value="x86_64"
        ), self.assertRaisesRegex(ValueError, "output directory must be absent"):
            native.qualify(args)
        self.assertEqual(marker.read_bytes(), b"prior result\n")

        absent = self.root / "absent"
        args.output = absent
        with mock.patch.object(native.platform, "system", return_value="Darwin"), self.assertRaisesRegex(
            ValueError, "native Linux host required"
        ):
            native.qualify(args)
        self.assertFalse(absent.exists())
        with mock.patch.object(native.platform, "system", return_value="Linux"), mock.patch.object(
            native.platform, "machine", return_value="aarch64"
        ), self.assertRaisesRegex(ValueError, "native x86_64 Linux host required"):
            native.qualify(args)
        self.assertFalse(absent.exists())

    def test_meaningful_elf_and_allocation_tail_are_distinct(self):
        capture = ROOT / "evidence/original/mayhem/deployed.so"
        candidate = self.root / "candidate.so"
        candidate.write_bytes(capture.read_bytes()[: native.MEANINGFUL_ELF_BYTES])
        receipt = native.verify_capture(ROOT, candidate)
        self.assertEqual(receipt["meaningful_elf_bytes"], 775416)
        self.assertEqual(receipt["excluded_zero_allocation_tail_bytes"], 1992)
        self.assertEqual(receipt["programdata_header_bytes"], 45)

        candidate.write_bytes(candidate.read_bytes() + b"\0")
        with self.assertRaisesRegex(ValueError, "meaningful ELF differs"):
            native.verify_capture(ROOT, candidate)

    def test_published_metadata_bindings_are_complete_and_unambiguous(self):
        evidence = json.loads((HERE / "published-metadata-bindings.json").read_text())
        rows = evidence["target_compile_bindings"]
        self.assertEqual(evidence["selected_windows_wrapper_records"], 176)
        self.assertEqual(len(rows), 85)
        self.assertEqual(len({(row["crate"], row["source"]) for row in rows}), 85)
        self.assertTrue(all(len(row["published_metadata"]) == 16 for row in rows))


if __name__ == "__main__":
    unittest.main()
