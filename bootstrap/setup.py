#!/usr/bin/env python3
"""Reproduce the declared workstation configuration; never update existing repos."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "bootstrap"
STEPS = ("packages", "directories", "repositories", "links", "kanata", "services", "copyq", "plugins", "study_platform")


class Setup:
    def __init__(self, args):
        self.args = args
        self.home = Path.home()
        self.failures = 0
        self.pending = 0
        self.backup = self.home / ".local/state/dotfiles/backups" / str(time.time_ns())

    def report(self, marker, message):
        print(f"{marker} {message}", flush=True)

    def need(self, message):
        self.pending += 1
        self.report("○", message)

    def run(self, command, **kwargs):
        if self.args.dry_run:
            self.report("→", shlex.join(map(str, command)))
            return
        subprocess.run(list(map(str, command)), check=True, **kwargs)

    def home_path(self, relative):
        p = Path(relative)
        if p.is_absolute() or ".." in p.parts:
            raise ValueError(f"Expected home-relative path: {relative}")
        return self.home / p

    def preserve(self, path):
        if path.exists() or path.is_symlink():
            destination = self.backup / path.relative_to(self.home)
            destination.parent.mkdir(parents=True, exist_ok=True)
            path.rename(destination)
            self.report("✓", f"Backed up {path} to {destination}")

    def link(self, source, destination):
        if not source.exists():
            raise ValueError(f"Missing dotfiles source: {source}")
        if destination.is_symlink() and destination.resolve() == source.resolve():
            return
        if self.args.check:
            self.need(f"Link {destination} → {source}")
        elif self.args.dry_run:
            self.report("→", f"Link {destination} → {source} (back up conflicts)")
        else:
            self.preserve(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(source, target_is_directory=source.is_dir())

    def rendered(self, source):
        return (source.read_text().replace("/home/pt/dev/dotfiles", str(ROOT))
                .replace("/home/pt/dev/config/dotfiles", str(ROOT))
                .replace("/home/pt", str(self.home)))

    def packages(self):
        if not Path("/etc/fedora-release").exists():
            raise RuntimeError("Package installation currently supports Fedora only")
        names = [line for line in (MANIFEST / "packages-fedora.txt").read_text().splitlines()
                 if line and not line.startswith("#")]
        installed = set(subprocess.check_output(["rpm", "-qa", "--qf", "%{NAME}\n"], text=True).splitlines())
        missing = [p for p in names if p not in installed]
        if missing:
            if self.args.check:
                self.need("Install packages: " + " ".join(missing))
            else:
                self.run(["sudo", "dnf", "install", "-y", *missing])

    def directories(self):
        for relative in json.loads((MANIFEST / "directories.json").read_text()):
            p = self.home_path(relative)
            if not p.is_dir():
                if self.args.check:
                    self.need(f"Create directory {p}")
                elif self.args.dry_run:
                    self.report("→", f"Create directory {p}")
                else:
                    p.mkdir(parents=True, exist_ok=True)

    def repositories(self):
        for repo in json.loads((MANIFEST / "repositories.json").read_text()):
            p = self.home_path(repo["path"])
            if p.exists() or p.is_symlink():
                if not (p / ".git").exists():
                    raise RuntimeError(f"Repository destination exists without Git metadata: {p}")
                # No pull, reset, branch switch, or checkout in existing repositories.
                continue
            if self.args.check:
                self.need(f"Clone {repo['path']}")
                continue
            command = ["git", "clone", "--recurse-submodules"]
            if repo.get("branch"):
                command += ["--branch", repo["branch"]]
            command += ["--", repo["url"], str(p)]
            if not self.args.dry_run:
                p.parent.mkdir(parents=True, exist_ok=True)
            self.run(command, env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"})

    def links(self):
        links = json.loads((MANIFEST / "links.json").read_text())
        for destination, source in links.items():
            self.link(ROOT / source, self.home_path(destination))
        # Link complete skills, including future supporting files.
        for folder in sorted((ROOT / "codex-skills").iterdir()):
            if (folder / "SKILL.md").exists():
                self.link(folder, self.home / ".codex/skills" / folder.name)
        self.skill_creator_addendum()
        # Expose maintained helpers without linking bytecode or source-only files.
        for helper in sorted((ROOT / "bin").iterdir()):
            if helper.is_file() and os.access(helper, os.X_OK):
                self.link(helper, self.home / ".local/bin" / helper.name)
        for desktop in (ROOT / "applications").glob("*.desktop"):
            self.link(desktop, self.home / ".local/share/applications" / desktop.name)
        # Add personal Git defaults through an include, retaining local identity/settings.
        config = self.home / ".gitconfig"
        include = str(ROOT / "gitconfig")
        result = subprocess.run(["git", "config", "--file", str(config), "--get-all", "include.path"], capture_output=True, text=True)
        if include not in result.stdout.splitlines():
            if self.args.check:
                self.need("Include dotfiles Git configuration")
            else:
                self.run(["git", "config", "--file", str(config), "--add", "include.path", include])

    def skill_creator_addendum(self):
        """Keep a local convention without copying/replacing the bundled skill."""
        target = self.home / ".codex/skills/.system/skill-creator/SKILL.md"
        if not target.is_file():
            self.need("Install Codex's bundled skill-creator, then rerun --only links for its Obsidian notification convention")
            return
        source = ROOT / "codex/skill-overrides/skill-creator-obsidian.md"
        start = "<!-- dotfiles:skill-creator-obsidian:start -->"
        end = "<!-- dotfiles:skill-creator-obsidian:end -->"
        original = target.read_text()
        if original.count(start) != original.count(end) or original.count(start) > 1:
            raise ValueError("Malformed managed skill-creator addendum; preserve it for inspection")
        block = start + "\n" + source.read_text().rstrip() + "\n" + end
        if start in original:
            updated = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: block, original, flags=re.S)
        else:
            updated = original.rstrip() + "\n\n" + block + "\n"
        if updated == original:
            return
        if self.args.check:
            self.need("Apply skill-creator Obsidian notification convention")
        elif self.args.dry_run:
            self.report("→", "Apply skill-creator Obsidian notification convention (back up original)")
        else:
            self.preserve(target)
            target.write_text(updated)
            self.report("✓", "Applied skill-creator Obsidian notification convention")

    def kanata(self):
        binary = shutil.which("kanata")
        version = subprocess.check_output([binary, "--version"], text=True).strip() if binary else ""
        if version != "kanata 1.10.1":
            if self.args.check:
                self.need("Install Kanata 1.10.1 (version used with this configuration)")
                return
            self.run(["cargo", "install", "--locked", "--version", "1.10.1", "kanata"])
            self.run(["sudo", "install", "-m", "755", self.home / ".cargo/bin/kanata", "/usr/bin/kanata"])
            binary = "/usr/bin/kanata"
        if binary and not self.args.dry_run:
            self.run([binary, "--check", "--cfg", ROOT / "kanata/config.kbd"])
        target = Path("/etc/systemd/system/kanata.service")
        content = self.rendered(ROOT / "systemd/system/kanata.service")
        matching = target.exists() and target.read_text() == content
        if not matching:
            if self.args.check:
                self.need("Install rendered Kanata system unit")
            else:
                generated = self.home / ".local/state/dotfiles/rendered/kanata.service"
                if not self.args.dry_run:
                    generated.parent.mkdir(parents=True, exist_ok=True)
                    generated.write_text(content)
                    self.run(["systemd-analyze", "verify", generated])
                    if target.exists():
                        self.run(["sudo", "cp", "--preserve", target, str(target) + ".dotfiles-backup-" + str(time.time_ns())])
                self.run(["sudo", "install", "-m", "644", generated, target])
                self.run(["sudo", "systemctl", "daemon-reload"])
        if self.args.check:
            result = subprocess.run(["systemctl", "is-enabled", "--quiet", "kanata.service"])
            if result.returncode:
                self.need("Enable Kanata system service")
        else:
            # Enable/start without restarting an already-running keyboard remapper.
            self.run(["sudo", "systemctl", "enable", "--now", "kanata.service"])

    def services(self):
        # The phone tunnel is conditional: its SSH alias and VPN client are restored separately.
        units = ["battery-watch.service", "kanata-layer-watch.service", "brave-shutdown.service", "mpris-proxy.service", "physio-log-laptop.service"]
        ssh_config = self.home / ".ssh/config"
        phone_ready = (shutil.which("tailscale") and ssh_config.exists()
                       and re.search(r"(?m)^\s*Host\s+[^\n]*\bandroid-phone\b", ssh_config.read_text()))
        if phone_ready:
            units.append("physio-phone-view.service")
            units.append("physio-log-sync.timer")
        else:
            self.need("Physio Log tunnel: install/sign in to Tailscale and restore the android-phone SSH alias/key")
        for unit in units + (["physio-log-sync.service"] if phone_ready else []):
            source = ROOT / "systemd/user" / unit
            if "/home/pt" in source.read_text() and self.home != Path("/home/pt"):
                raise RuntimeError(f"Make {source} portable before restoring on another username")
            self.link(source, self.home / ".config/systemd/user" / unit)
        if self.args.check:
            for unit in units:
                r = subprocess.run(["systemctl", "--user", "is-enabled", "--quiet", unit], capture_output=True)
                if r.returncode:
                    self.need(f"Enable user unit {unit}")
            return
        self.run(["systemctl", "--user", "daemon-reload"])
        for unit in units:
            # Graphical units start on next graphical login, not in an SSH session.
            self.run(["systemctl", "--user", "enable", unit])
        if os.environ.get("DISPLAY"):
            self.run(["systemctl", "--user", "start", "battery-watch.service", "kanata-layer-watch.service"])
        self.run(["systemctl", "--user", "start", "mpris-proxy.service"])
        self.run(["systemctl", "--user", "start", "physio-log-laptop.service"])
        if phone_ready:
            self.run(["systemctl", "--user", "start", "physio-phone-view.service"])
            self.run(["systemctl", "--user", "start", "physio-log-sync.timer"])

    def copyq(self):
        if not shutil.which("copyq") or not os.environ.get("DISPLAY"):
            self.need("CopyQ rule: run install.sh --only copyq in an X11 desktop session")
            return
        if self.args.check:
            # Read configuration without launching a GUI/server in check mode.
            config = self.home / ".config/copyq/copyq-commands.ini"
            if not config.exists() or "personal_store_secret_clipboard" not in config.read_text():
                self.need("Install CopyQ secret-history rule")
        else:
            self.run([sys.executable, ROOT / "bin/setup-copyq"])

    def deltaai(self):
        # Remote account configuration is opt-in, never part of laptop setup.
        if self.args.check:
            self.need("DeltaAI is remote: verify over an authenticated SSH session")
        else:
            self.run([sys.executable, ROOT / "deltaai/deploy.py"])

    def plugins(self):
        target = self.home / ".tmux/plugins/tpm"
        if not target.exists():
            if self.args.check:
                self.need("Install tmux plugin manager")
            else:
                self.run(["git", "clone", "https://github.com/tmux-plugins/tpm", target])
        if self.args.check:
            for name in ("tmux-sensible", "tmux-resurrect", "tmux-sessionx"):
                if not (target.parent / name).exists():
                    self.need(f"Install tmux plugin {name}")
        else:
            self.run([target / "bin/install_plugins"])

    def sleep_diagnostics(self):
        # Hardware-specific and explicitly selected: never enable on unknown machines.
        recipe = ROOT / "bootstrap/setup-amd-sleep"
        if self.args.check:
            result = subprocess.run([recipe, "--check"], check=False)
            if result.returncode:
                self.need("AMD sleep diagnostics: run install.sh --only sleep_diagnostics on the supported ThinkPad")
        else:
            self.run([recipe])

    def browser_automation(self):
        python = self.home / ".local/share/codex-browser/venv/bin/python"
        if not shutil.which("brave-browser-stable"):
            self.need("Install Brave before setting up the automation browser")
            return
        ready = python.exists() and subprocess.run(
            [python, "-c", "import playwright; from importlib.metadata import version; assert version('playwright') == '1.56.0'"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if not ready:
            if self.args.check:
                self.need("Install the browser automation Python environment")
            else:
                self.run([sys.executable, "-m", "venv", python.parent.parent])
                self.run([python, "-m", "pip", "install", "playwright==1.56.0"])

    def study_platform(self):
        source = self.home / "dev/personal/automation/personal-scripts/study-platform"
        if not (source / "requirements.txt").is_file():
            self.need("Restore study-platform source from personal-scripts (including unpublished changes)")
            return
        python = self.home / ".local/share/study-platform/venv/bin/python"
        ready = python.exists() and subprocess.run(
            [python, "-c", "from importlib.metadata import version; assert version('fsrs') == '6.3.3' and version('textual') == '8.2.8'"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if not ready:
            if self.args.check:
                self.need("Install study-platform Python dependencies")
            else:
                self.run([sys.executable, "-m", "venv", python.parent.parent])
                self.run([python, "-m", "pip", "install", "-r", source / "requirements.txt"])
        self.link(source / "study", self.home / ".local/bin/study")

    def main(self):
        selected = self.args.only or STEPS
        for step in selected:
            self.report("→", step)
            before = self.pending
            try:
                getattr(self, step)()
                if self.pending == before:
                    self.report("✓", f"{step}: {'planned' if self.args.dry_run else 'complete'}")
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                self.failures += 1
                self.report("✗", f"{step}: {error}")
        self.report("→", f"{self.failures} failed steps; {self.pending} pending actions. See bootstrap/AUDIT.md for data/authentication and app-specific gaps.")
        return 1 if self.failures or self.pending else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print changes without writing, installing, cloning, or starting services")
    mode.add_argument("--check", action="store_true", help="Read-only check; exit 1 when changes are needed")
    parser.add_argument("--only", nargs="+", choices=(*STEPS, "deltaai", "sleep_diagnostics", "browser_automation"), help="Run selected setup steps (DeltaAI, sleep diagnostics, and browser automation are opt-in)")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as your regular user; individual system steps use sudo")
    return Setup(args).main()


if __name__ == "__main__":
    sys.exit(main())
