#!/usr/bin/env python3
"""Deploy personal shell/Neovim config via SSH or an existing idle tmux SSH pane."""
import argparse
import base64
import io
from pathlib import Path
import shlex
import subprocess
import tarfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--host", default="praita@dtai-login.delta.ncsa.illinois.edu")
parser.add_argument("--tmux-pane", help="Use an existing authenticated session at an idle shell prompt")
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()
payload = io.BytesIO()
with tarfile.open(fileobj=payload, mode="w:gz") as archive:
    for folder in ("deltaai", "nvim"):
        for source in sorted((root / folder).rglob("*")):
            if (source.is_file() and source.name != ".nvimlog" and source.suffix != ".log"
                    and not any(part in {"__pycache__", ".git", ".codex"} for part in source.parts)):
                archive.add(source, arcname=str(source.relative_to(root)), recursive=False)
encoded = base64.b64encode(payload.getvalue()).decode()
remote = '''import base64,io,os,subprocess,tarfile,tempfile
stage=tempfile.mkdtemp(prefix="deltaai-setup-")
archive=tarfile.open(fileobj=io.BytesIO(base64.b64decode(PAYLOAD)),mode="r:gz")
archive.extractall(stage)
subprocess.check_call(["bash",stage+"/deltaai/install.sh"])
subprocess.check_call(["bash",stage+"/deltaai/install-nvim.sh"])
print("DELTA_SETUP_COMPLETE")
'''.replace("PAYLOAD", repr(encoded))
command = "python3 -c " + shlex.quote(remote)
if args.dry_run:
    print("Would install personal shell and full Neovim config via " + (args.tmux_pane or args.host))
    print("Compressed config payload: %d bytes" % len(payload.getvalue()))
elif args.tmux_pane:
    # Bracketed paste keeps multiline commands intact in the existing Zsh shell.
    snapshot = subprocess.check_output(["tmux", "capture-pane", "-p", "-t", args.tmux_pane], text=True).rstrip()
    if not snapshot.endswith("$ ".rstrip()):
        parser.error("Pane is not at the expected idle shell prompt; return to the shell first.")
    subprocess.run(["tmux", "load-buffer", "-b", "deltaai-setup", "-"], input=command.encode(), check=True)
    subprocess.run(["tmux", "paste-buffer", "-p", "-d", "-b", "deltaai-setup", "-t", args.tmux_pane], check=True)
    subprocess.run(["tmux", "send-keys", "-t", args.tmux_pane, "Enter"], check=True)
    print("Deployment started; verify DELTA_SETUP_COMPLETE in pane " + args.tmux_pane)
else:
    subprocess.run(["ssh", args.host, command], check=True)
