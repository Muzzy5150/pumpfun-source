#!/usr/bin/env python3
"""Run SDK rust-lld with an admitted text order and exact bound input copies."""
import os
import sys
from pump_text_layout import prepare_link

command = prepare_link(sys.argv[1:], os.environ)
os.execv(command[0], command)
