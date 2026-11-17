# New machine setup

After installing Fedora, Git, and Python 3, and configuring SSH access to your
private GitHub/GitLab repositories:

```sh
git clone git@github.com:petteriraita/dotfiles.git ~/dev/config/dotfiles
~/dev/config/dotfiles/install.sh
```

The script shows ✓ completed steps, ○ pending actions, and ✗ failed steps.
System installation uses sudo. Run as your regular user, not root.
Select an i3/X11 session at login; the keyboard/window automation assumes X11.
Run inside that desktop session to configure CopyQ immediately. An SSH-only run
reports the pending CopyQ step; repeat `install.sh --only copyq` after login.

```sh
~/dev/config/dotfiles/install.sh --dry-run
~/dev/config/dotfiles/install.sh --check
~/dev/config/dotfiles/install.sh --only links copyq
python3 ~/dev/config/dotfiles/bootstrap/audit.py
```

`--check` is read-only and exits nonzero if setup is incomplete. `--dry-run`
prints actions without writing, cloning, installing, or enabling services.
Failures do not conceal later steps and produce a nonzero final status.
Reruns preserve existing repositories and back up conflicting configuration
under `~/.local/state/dotfiles/backups/` before linking maintained sources.
No existing repository is pulled, reset, or switched to another commit.

## Maintained inputs

- `packages-fedora.txt`: selected direct dependencies, not the old Ubuntu dump.
- `directories.json`: grouping directories, including DTU/UIUC semesters.
- `repositories.json`: destination and remote for each durable repository.
  New clones follow the recorded branch tip. Old `recorded_commit` fields are
  historical reference, not instructions to detach a fresh workstation at an
  old revision. Earlier deliberately selected backup remotes are preserved.
- `links.json`: configuration sources and their destinations.
- `setup.py`: Kanata install/unit recipe, selected user services, the conditional Physio Log phone tunnel, CopyQ, tmux.
- `../bin/setup-copyq`: repeatable CopyQ settings and password-history rule.
- `../deltaai/deploy.py`: optional `install.sh --only deltaai` deployment of the
  actual shell/Neovim setup to the authenticated remote account; not run by default.
- `AUDIT.md`: what remains outside automatic restoration and why.

The earlier `personal-scripts/workspace/restore-workspace.sh` remains a separate
historical snapshot-recovery tool. It restores recorded commits and directories;
this installer is the entry point for the current workstation configuration.
Its full-workspace backup script still matters for uncommitted and non-Git data.

## Maintaining this over time

Use the `dotfiles-bootstrap` skill for durable workstation changes. Update the
relevant manifest or repeatable recipe as part of the change. Add durable new
personal/course repositories; temporary clones and vendored submodules normally
do not need independent entries. Local-only repos need a backup/remote decision.
Do not silently replace backup remotes with upstream origins.

Keep credentials, browser profiles, clipboard history, database contents, SSH
private keys, OAuth tokens, caches, and build output out of these manifests and
configuration sources. Authenticate/restore data separately. Setup code can be
versioned without saving runtime data. Git commits and pushes remain explicit
actions: new files do not reach another machine until published to the remote.

## Kanata

Setup installs the known-working 1.10.1 release using Cargo, checks the config,
renders the system unit for the actual home/repository path, enables and starts
it, then enables the user layer watcher. An already-running remapper is not
restarted. Changes to running remapper behavior still use the kanata-setup skill.
The tracked config currently selects this user's keyboard device names: a
different keyboard may require updating that list. The setup deliberately does
not import the old passwordless sudo rule or enable laptop-specific power fixes.

Build/install reference: https://github.com/jtroo/kanata#build-it-yourself

## AMD sleep diagnostics

On the ThinkPad 21QR003WMX, `install.sh --only sleep_diagnostics` restores the
pinned AMD debug tools, ACPI dependencies, sleep hook, and device timing unit.
The recipe is opt-in and refuses other hardware or a different account path.
It preserves existing conflicting hooks, units and tool checkouts. The older
`setup-amd-sleep-root` script is an incident-specific kernel installer and is
not run by bootstrap. Fedora kernel updates are managed separately.
The investigation helpers currently assume `/home/pt/dev/config/dotfiles`;
their private logs and `/var/lib/amd-s2idle/data.db` require separate backup.
The actual sleep/wake test requires user confirmation and is never automatic.
New-machine installation and hardware sleep behavior have not been tested.

## Physio Log laptop and phone access

The installer links, enables, and starts `physio-log-laptop.service` at
`http://127.0.0.1:18768/`. Its records live in
`~/.local/share/physio-log/workouts/` and require a separate data restore.
The laptop copy shows its last successful phone sync time. The optional
`physio-log-sync.timer` retries a conflict-checked, two-way workout merge each
minute when the phone tunnel is available; both exports are backed up before
an import. Workout files and phone diary imports still need separate data
restoration on a new machine.

The installer also links and enables `physio-phone-view.service` when Tailscale
is installed and `~/.ssh/config` contains the `android-phone` alias. The unit
forwards only laptop port 18766 to the phone's Physio Log port 8766 and retries
if the phone is temporarily unreachable. The phone's
Tailscale sign-in, SSH key, Physio Log source and workout files must be restored
separately. After that, copy `bin/setup-physio-phone-services` to the phone and
run it once in Termux to install `termux-services`, enable supervised `sshd`
and Physio Log, and replace the old one-shot boot scripts. The script is
idempotent and backs up those scripts on the phone. Android's Always-on VPN setting for Tailscale
must be enabled on the phone itself; a laptop service cannot keep a disconnected
phone VPN online. If the phone is offline, the tunnel retries and the laptop
copy at port 18768 remains available with the last synced records.

## Codex launch context

`codexa` and `codexas` intentionally keep the Codex working directory at
`/home/pt`, while `shell/common.sh` captures the invoking shell directory and
passes it as session developer context through `-c developer_instructions=...`.
The model can distinguish the launch/project folder from its home working
directory without running a command. Resume/fork invocations receive the current
launch folder too. `install.sh --only links` restores this through the existing
`.config/shell` link. Source `~/.config/shell/common.sh` or open a new shell
after changing the wrapper. Direct `codex` launches do not use these wrappers.

## Phone scheduling skill

`install.sh --only links` restores the complete `codex-skills/schedule/` folder.
The links step also applies `codex/skill-overrides/skill-creator-obsidian.md` as a
marked addendum to the installed bundled skill-creator, preserving upstream
content and backing up changes. Rerun after Codex replaces bundled skills; a
missing bundled skill is reported as pending rather than creating a partial copy.
The convention explicitly notifies the user when the skill description is saved
in the Obsidian catalog.

The schedule helpers are CLI/API-only. Google Contacts uses a separate persistent
OAuth credential and standard-library Python; the client config, consent,
project API enablement and token must be restored privately. Clock Local API is
a locally modified GPL Fossify Clock build with a Termux-only provider. Its pinned
source additions and build recipe are under the skill; JDK 21 and zip/unzip are
declared here. The Android SDK is an external build prerequisite, not installed
by this entry point. See `codex-skills/schedule/references/local-api-setup.md` for
SDK sources, signing-key/data restoration requirements and actual test status.

APK/client installation, phone notification/exact-alarm permissions, Tailscale
sign-in, SSH key/config, Termux sshd/Boot and saved alarm data require separate
restoration. The laptop installer does not perform phone UI actions. Native client
framework bootstrap is Android-version-sensitive and needs rechecking after OS
upgrades. Daily alarm commands use SSH, not Wireless debugging or recurring ADB
pairing codes. Contacts API commands do not depend on phone connectivity. A saved
alarm's local firing still requires the phone/app/permissions to function.

## Tmux prompt navigation

The maintained `.tmux.conf` link restores prefix-p/n and copy-mode Ctrl-p/n.
In a pane running `codex`, these search backward/forward for the `› ` user-message
prefix; shell panes use OSC 133 prompt markers as before. Codex navigation sets
the latest copy-mode search, so n/N subsequently repeat it. Press q to leave
copy mode and return to the live conversation. Reload an existing tmux server
with `tmux source-file ~/.tmux.conf` after changing the configuration.

## Anki and Discord word deletion

The Kanata focus watcher selects the existing `brave` layer for the observed
Anki (`"anki", "Anki"`) and Discord (`"discord", "discord"`) X11 window classes.
Ctrl+W deletes the previous word and Alt+W emits native Ctrl+W. The installer
restores this through the maintained watcher and `kanata-layer-watch.service`.
After watcher edits, restart only the user watcher service.

## Sioyek marks

The maintained `.config/sioyek` link restores `keys_user.config`, including
`goto_mark '`: press apostrophe, then the mark letter (for example `'c`).

## Browser automation profile

Run `install.sh --only browser_automation` to install the pinned Playwright
Python environment. Brave must already be installed. The helper at
`browser-automation/browser.py` uses a separate persistent Brave profile under
`~/.local/share/codex-browser/profile`; it never attaches to the daily profile.
For example, run `~/.local/share/codex-browser/venv/bin/python
~/dev/config/dotfiles/browser-automation/browser.py open https://canvas.illinois.edu/`
to open a visible sign-in window. Close that window before using the profile
headlessly. Accounts must be signed in separately; MFA and session expiration can
require renewed interaction. Passwords, cookies, and profile data are private
runtime state and are not backed up or restored by this installer. Do not run
multiple automation browsers using the profile at the same time.

## Local study platform

`install.sh --only study_platform` links the `study` launcher from the existing
`personal-scripts/study-platform` repository folder and installs pinned direct
Python dependencies in `~/.local/share/study-platform/venv`. The default install
also runs this step after restoring repositories. The app uses the user's actual
Neovim, tmux, VimTeX, Sioyek and Codex; their dependencies and authentication
must be available separately. See the app's README for usage and limitations.

Learning documents, attempts and scheduler state under
`~/.local/share/study-platform/` need a separate private backup; no credentials
or study data are included in dotfiles. The new app files and this setup remain
local until committed and published, so a fresh clone cannot yet restore them.
