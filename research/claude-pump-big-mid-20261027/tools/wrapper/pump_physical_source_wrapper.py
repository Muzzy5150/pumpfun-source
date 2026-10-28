#!/usr/bin/env python3
"""RUSTC_WRAPPER shim: append BM_EXTRA_RUSTC_ARGS (JSON list) to the pump_recovered crate's rustc call only,
then defer to the Pump harness's own source wrapper (unchanged behaviour for every other crate)."""
import json, os, sys
HARNESS_WRAPPER = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-pump-work/harness/pump_physical_source_wrapper.py'
args = sys.argv[1:]
if 'pump_recovered' in args and '--crate-name' in args and args[args.index('--crate-name') + 1] == 'pump_recovered':
    args += json.loads(os.environ.get('BM_EXTRA_RUSTC_ARGS', '[]'))
os.execv(sys.executable, [sys.executable, '-B', HARNESS_WRAPPER, *args])
