#!/usr/bin/env python3
"""Read-only inventory of recovery coverage; no application secrets are read."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
repos = json.loads((ROOT / "bootstrap/repositories.json").read_text())
declared = {str(HOME / row["path"]) for row in repos}
ignored = {".git", "node_modules", ".venv", "venv", "build", "dist", "target", "__pycache__", ".obsidian", ".cache"}

print("Repositories not declared (nested/vendor repos may intentionally be excluded):")
missing = []
for path, directories, files in os.walk(HOME / "dev"):
    is_repo = ".git" in directories or ".git" in files
    directories[:] = [d for d in directories if d not in ignored]
    if is_repo and path not in declared:
        result = subprocess.run(["git", "-C", path, "remote", "get-url", "origin"], capture_output=True, text=True)
        # Do not print remote URLs: they can contain embedded credentials.
        missing.append(path)
        print(f"  ○ {path}: {'has origin' if result.returncode == 0 else 'NO ORIGIN — needs backup/remote'}")
print(f"  {len(repos)} declared; {len(missing)} not declared")

print("\nEnabled user services not selected for automatic machine setup:")
selected = {"battery-watch.service", "kanata-layer-watch.service", "brave-shutdown.service"}
result = subprocess.run(["systemctl", "--user", "list-unit-files", "--state=enabled", "--no-legend", "--no-pager"], capture_output=True, text=True)
if result.returncode:
    print("  ○ User systemd session unavailable")
for line in result.stdout.splitlines():
    unit = line.split()[0]
    local = HOME / ".config/systemd/user" / unit
    if local.exists() and unit not in selected:
        canonical = ROOT / "systemd/user" / unit
        print(f"  ○ {unit}: {'canonical unit exists; recipe needed' if canonical.exists() else 'local-only unit'}")

print("\nBroken configuration/helper links (excluding browser/app profile internals):")
for folder in [HOME / ".local/bin", HOME / ".config", HOME / ".config/systemd/user", HOME / ".codex/skills", HOME]:
    if not folder.exists():
        continue
    for item in sorted(folder.iterdir()):
        if item.is_symlink() and not item.exists():
            print(f"  ○ {item}")

print("\nDeclared configuration destinations not linked to their maintained source:")
for destination, source in json.loads((ROOT / "bootstrap/links.json").read_text()).items():
    target = HOME / destination
    if not target.is_symlink() or target.resolve() != (ROOT / source).resolve():
        print(f"  ○ {target}")

print("\nRead bootstrap/AUDIT.md for runtime data, credentials, hardware, and app install gaps.")
