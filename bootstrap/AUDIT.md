# Workstation reproducibility audit — 2026-10-29

## Found and covered

The old recovery entry point is
`~/dev/personal/automation/personal-scripts/workspace/restore-workspace.sh`.
Its manifests cover directory grouping and historical repository snapshots,
including DTU and UIUC semesters. It does not install packages or config.

The dotfiles `install.sh` now declares Fedora desktop/CLI packages, that directory
layout, repository clones, maintained dotfile links, whole personal skill links,
executable helpers, Git defaults, Kanata and its watcher, selected user services,
CopyQ password history, its Alt+V toggle, selected CopyQ preferences, and tmux
plugin installation. New repository entries include personal-scripts,
fast-replay-viewer, mars-stats-static, and low-elo-stopper.

Previously local-only Kitty theme/tmux startup, i3status, gammastep, and ZDOTDIR
are now in dotfiles. Battery-watch's unit uses `%h` instead of `/home/pt`.
Conflicting live files are backed up, not discarded.

## Remaining recovery requirements

DeltaAI now has an opt-in shell/Neovim deployment recipe (`install.sh --only
deltaai`). It copies the actual local editor configuration, installs official
ARM64 Neovim 0.11.5, and adapts yanks through OSC 52/tmux passthrough. Theme,
cursor settings and clipboard yanks were checked on the authenticated cluster
session. Optional local debuggers/LSP servers still depend on remote ARM64
packages; this does not provision a GPU environment or alter cluster jobs.

| Area | Current limitation / next concrete work |
| --- | --- |
| Publishing | Many existing dotfiles edits/new skills were already uncommitted. This audit does not commit or push them. Publish reviewed changes before relying on remote recovery. |
| Authentication | GitHub/GitLab SSH, Google/OAuth, Garmin, OneDrive, Syncthing pairing, browser/extension sign-in, and password database unlocking require credentials or pairing. Do not store them in dotfiles. |
| Local data | `health-stats-dashboard` has no origin remote. Other non-Git projects, datasets, downloads, untracked work, and dirty repository changes require a separate backup. A manifest cannot recreate them. |
| App services | The Physio Log laptop app is enabled at port 18768, with its local workout data in `~/.local/share/physio-log/workouts/`. On 2026-11-06, 17 workouts and 14 diary days were merged with the phone. `physio-log-sync.timer` retries every minute through the phone tunnel at port 18766 and backs up both exports before changes. The health dashboard reads the laptop copy, so its exercise bars remain available when the phone tunnel drops. On 2026-11-05, `termux-services` and supervised `sshd` and Physio Log were installed on the phone with `bin/setup-physio-phone-services`; both restarted after deliberate process kills. Android may still stop the whole Termux app; the laptop service remains available independently. SSH keys, Tailscale sign-in, phone data and battery settings remain separate restoration steps. Health dashboard/Garmin import, Mars dashboards, Android SSH tunnel, and zombie-trailer-park still need project dependencies/data/authentication and explicit recipes before automatic enablement. |
| Push-to-talk | Repo is cloned and helpers/i3 bindings restored. Python environments, model weights, CUDA/audio dependencies and worker validation still need a project-specific installer. |
| Desktop apps | Brave, VS Code, Obsidian, Anki, Sioyek binary, Steam, Calibre, OBS and other third-party apps need maintained vendor/Flatpak recipes, rather than copying binaries or blindly importing an old package dump. |
| Fonts | Kitty requests JuliaMono; Neovim may need Nerd Font glyphs. Font binaries were not copied into Git; add maintained font download/package recipes. |
| Language tools | Conda environments, .NET, Isabelle, Node toolchains, global npm/Python tools and Codex need version-aware installers. Old environment/package dumps are reference only. |
| Editor plugins | tmux plugins are automated. Neovim plugin/tool downloads and VS Code extensions remain application setup work. |
| Hardware | Kanata device names, touchpad identity, display EDID/hotplug, brightness schedules and AMD suspend diagnostics are machine-specific. AMD diagnostics have an opt-in recipe, `install.sh --only sleep_diagnostics`, restricted to ThinkPad 21QR003WMX and the current home path; private incident data needs separate backup. Do not automatically apply old laptop fixes to unknown hardware. |
| Shell choice | Zsh config and ZDOTDIR are restored. Changing the account login shell with `chsh` remains manual. |
| Other settings | MIME handlers, browser extensions, dconf, Syncthing folders, OneDrive content and phone integration are not fully declared yet. The schedule CLI/API source is restored by skill linking. Contacts OAuth/project consent, Tailscale/SSH authentication, Android SDK/signing key, local Fossify API APK/client installation, phone permissions and alarm data need separate restoration. Contacts create/readback/refresh passed; native app build/client identity passed, but installed-device alarm tests are pending. No phone UI automation is allowed. |
| Portability | i3/helper/app scripts still contain the present username's absolute paths. Kanata's system unit is rendered, battery unit is portable, but a different username requires further auditing. Fedora/i3/X11 is the supported target. |

Run `python3 bootstrap/audit.py` for an updated inventory of repository coverage,
enabled user units, broken symlinks, and live configuration links. It reads
metadata only and does not print clipboard/password/token contents.

## Verification limits

Installer behavior is tested in temporary homes with command execution mocked:
backup/idempotence, dry-run side effects, preserving existing repositories,
branch-aware clone commands, and failure aggregation. The current workstation
gets read-only check/dry-run validation. A clean Fedora VM installation has not
been executed; package downloads, third-party services, and hardware behavior
are not represented as proven. The gaps above remain visible rather than being
counted as fully restored.

- Local study platform: the app source and installer integration are currently uncommitted; publish the existing personal-scripts and dotfiles changes for new-machine restoration. Back up private `~/.local/share/study-platform/` learning data and restore Codex authentication separately.
