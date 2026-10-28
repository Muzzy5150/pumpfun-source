#!/usr/bin/env python3
"""Apply the reviewed linker hook only to the main Pump cdylib compilation."""
import os
import sys
from pump_text_layout import rustc_command

command = rustc_command(sys.argv[1], sys.argv[2:], os.environ)
os.execv(command[0], command)
