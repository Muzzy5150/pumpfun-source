"""Exercise complete source-snapshot fidelity through the real integration CLI."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HARNESS = Path(__file__).resolve().parent


def snapshot(root):
    root = Path(root)
    return {
        path.relative_to(root).as_posix(): {
            'bytes': path.read_bytes(),
            'executable': bool(path.stat().st_mode & 0o111),
        }
        for path in root.rglob('*') if path.is_file()
    }


@unittest.skipUnless(
    shutil.which('git') and shutil.which('diff') and shutil.which('patch'),
    'requires the real composition tools',
)
class CompositionFidelityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='composition-fidelity-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        harness = self.root / 'reconstruction/harness'
        harness.mkdir(parents=True)
        for name in ('integrate.py', 'source_inputs.py'):
            shutil.copy2(HARNESS / name, harness / name)
        self.tool = harness / 'integrate.py'

    def crate(self, name, files=None, executable=()):
        root = self.root / name
        contents = {
            'Cargo.toml': (
                b'[package]\nname = "composition_fixture"\nversion = "0.0.0"\n'
                b'edition = "2021"\n\n[lib]\npath = "src/lib.rs"\n'
            ),
            'Cargo.lock': (
                b'version = 3\n\n[[package]]\nname = "composition_fixture"\n'
                b'version = "0.0.0"\n'
            ),
            'src/lib.rs': (
                b'pub mod target;\n'
                b'pub const IMAGE: &[u8] = include_bytes!("../assets/image.bin");\n'
                b'pub const TARGET_DATA: &[u8] = include_bytes!("../assets/target/data.bin");\n'
            ),
            'src/target/mod.rs': b'pub const VALUE: u8 = 1;\n',
            'assets/target/data.bin': b'base-target-data\x00',
            'assets/image.bin': b'base-image\x00\xff',
            'scripts/executable-tool.sh': b'#!/bin/sh\nexit 0\n',
            **(files or {}),
        }
        for relative, data in contents.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        for relative in executable:
            os.chmod(root / relative, (root / relative).stat().st_mode | 0o111)
        return root

    def compose(self, base, parts, bases=(), expected_returncode=0, name='test'):
        argv = [sys.executable, '-B', str(self.tool), '--name', name,
                '--base-src', str(base), '--no-build']
        for label, part in parts:
            argv += ['--part', f'{label}={part}']
        for label, derived in bases:
            argv += ['--base-of', f'{label}={derived}']
        result = subprocess.run(argv, cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected_returncode, result.stdout + result.stderr)
        output = self.root / 'reconstruction/integ' / name
        report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
        return output, report

    def test_binary_mode_nested_source_and_native_build_are_lossless(self):
        base = self.crate('base')
        part = self.crate('part', {
            'src/target/mod.rs': b'pub const VALUE: u8 = 2;\n',
            'assets/target/data.bin': b'part-target-data\x00',
            'assets/image.bin': b'part-image\x00\xfe',
        }, executable=('scripts/executable-tool.sh',))
        before = [snapshot(path) for path in (base, part)]

        output, report = self.compose(base, [('change', part)])

        self.assertEqual(snapshot(output / 'src'), before[1])
        self.assertEqual([snapshot(path) for path in (base, part)], before)
        self.assertEqual(report['parts'], [{
            'label': 'change', 'status': 'applied',
            'files': ['assets/image.bin', 'assets/target/data.bin',
                      'scripts/executable-tool.sh', 'src/target/mod.rs'],
        }])
        if shutil.which('cargo'):
            built = subprocess.run([
                'cargo', 'check', '--locked', '--quiet',
                '--manifest-path', str(output / 'src/Cargo.toml'),
                '--target-dir', str(self.root / 'cargo-target'),
            ], capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stderr)

    def test_competing_text_and_binary_parts_fail_the_composition(self):
        base = self.crate('conflict-base', {'src/choice.rs': b'pub const CHOICE: u8 = 1;\n'})
        first = self.crate('conflict-first', {
            'src/choice.rs': b'pub const CHOICE: u8 = 2;\n',
            'assets/image.bin': b'first-image\x00\x01',
        })
        second = self.crate('conflict-second', {
            'src/choice.rs': b'pub const CHOICE: u8 = 3;\n',
            'assets/image.bin': b'second-image\x00\x02',
        })

        output, report = self.compose(
            base, [('first', first), ('second', second)], expected_returncode=1)

        self.assertEqual([part['status'] for part in report['parts']],
                         ['applied', 'conflict'])
        self.assertEqual((output / 'src/src/choice.rs').read_bytes(),
                         b'pub const CHOICE: u8 = 2;\n')
        self.assertEqual((output / 'src/assets/image.bin').read_bytes(),
                         b'first-image\x00\x01')
        self.assertNotIn('build', report)
        self.assertNotIn('score', report)

    def test_nonconflicting_parts_keep_explicit_derivation_provenance(self):
        base = self.crate('derived-base', {
            'baseline.txt': b'selected baseline\n',
            'src/one.rs': b'pub const ONE: u8 = 1;\n',
            'src/two.rs': b'pub const TWO: u8 = 1;\n',
        })
        derived = self.crate('other-baseline', {
            'baseline.txt': b'other baseline that must not be imported\n',
            'src/one.rs': b'pub const ONE: u8 = 1;\n',
            'src/two.rs': b'pub const TWO: u8 = 1;\n',
        })
        first = self.crate('derived-part', {
            'baseline.txt': b'other baseline that must not be imported\n',
            'src/one.rs': b'pub const ONE: u8 = 2;\n',
            'src/two.rs': b'pub const TWO: u8 = 1;\n',
        })
        second = self.crate('base-part', {
            'baseline.txt': b'selected baseline\n',
            'src/one.rs': b'pub const ONE: u8 = 1;\n',
            'src/two.rs': b'pub const TWO: u8 = 2;\n',
        })
        inputs_before = [snapshot(path) for path in (base, derived, first, second)]

        output, report = self.compose(
            base, [('first', first), ('second', second)], bases=[('first', derived)])

        expected = dict(inputs_before[0])
        expected['src/one.rs'] = inputs_before[2]['src/one.rs']
        expected['src/two.rs'] = inputs_before[3]['src/two.rs']
        self.assertEqual(snapshot(output / 'src'), expected)
        self.assertEqual([snapshot(path) for path in (base, derived, first, second)],
                         inputs_before)
        self.assertEqual((output / 'src/baseline.txt').read_bytes(), b'selected baseline\n')
        receipt = json.loads((output / report['source_inputs']['receipt']).read_text())
        result = json.loads((output / report['composed_source']['receipt']).read_text())
        self.assertEqual(receipt['schema'], 'pump-composition-inputs-v1')
        self.assertNotEqual(receipt['base']['sha256'], receipt['parts'][0]['derived']['sha256'])
        self.assertEqual(result['sha256'], report['composed_source']['sha256'])

    def test_unicode_crlf_missing_newline_creation_and_deletion_round_trip(self):
        base = self.crate('byte-base', {
            'src/é old.rs': b'// remove me\r\n',
            'src/mixed.rs': b'// context\r\npub const VALUE: u8 = 1;\n// no final LF',
        })
        part = self.crate('byte-part', {
            'src/é new.rs': b'// new file\r\n',
            'src/mixed.rs': b'// context\r\npub const VALUE: u8 = 2;\n// no final LF',
        })

        output, _report = self.compose(base, [('bytes', part)])

        self.assertEqual(snapshot(output / 'src'), snapshot(part))


if __name__ == '__main__':
    unittest.main()
