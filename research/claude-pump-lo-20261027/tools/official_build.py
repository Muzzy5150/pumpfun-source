#!/usr/bin/env python3
"""Run the frontier packet's archived builder on an arbitrary in-repo source directory (workspace layout)."""
import sys, importlib.util
from pathlib import Path
root = Path(sys.argv[1]).resolve(); pkt = root / sys.argv[2]; src = Path(sys.argv[3]).resolve(); out = Path(sys.argv[4]).resolve()
sys.path.insert(0, str(pkt / 'inputs/scripts'))
path = pkt / 'inputs/scripts/pump_build_verified.py'
spec = importlib.util.spec_from_file_location('archived_pump_builder', path); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b); b.ROOT = root
sys.argv = [str(path), '--source-directory', str(src), '--workspace-layout', '--registry-home', str(Path.home() / '.cargo'), '--output', str(out)]
b.main()
