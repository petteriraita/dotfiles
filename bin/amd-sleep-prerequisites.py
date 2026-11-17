#!/usr/bin/env python3
"""Run AMD's prerequisite checks without requesting suspend or installing hooks."""
import os
import sqlite3
import sys
from pathlib import Path

if os.geteuid() != 0:
    sys.exit('Administrator access is required for ACPI, PMC and driver checks.')

from amd_debug.prerequisites import PrerequisiteValidator

app = PrerequisiteValidator(tool_debug=True)
try:
    passed = app.run()
    app.report()
    print(f'\nAMD prerequisite checks passed: {passed}', flush=True)
finally:
    app.db.sync()
    if len(sys.argv) == 2:
        destination = Path(sys.argv[1]) / 'amd-baseline.db'
        with sqlite3.connect(destination) as backup:
            app.db.db.backup(backup)
        os.chmod(destination, 0o600)
        if 'SUDO_UID' in os.environ:
            os.chown(destination, int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID']))
if not passed:
    sys.exit(2)
