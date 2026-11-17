---
name: dotfiles-bootstrap
description: Keep durable workstation configuration and repository layout reproducible through the user's dotfiles installer. Use when changing local app settings, keyboard mappings, shell/editor configuration, services, installed tools, workspace directories, or creating durable personal/course repositories; also for new-machine setup audits. Not for ordinary project source edits or temporary clones.
---

# Dotfiles Bootstrap

The goal is one maintained setup command on a new Fedora/i3/X11 workstation,
with visible checkmarks and explicit pending work rather than years of manual
reconstruction. A live setting change is incomplete until its reproducible
source and installation path are updated, or a concrete limitation is recorded.

## Source of truth

- Dotfiles: `/home/pt/dev/config/dotfiles/`.
- Entry point: `install.sh`; behavior and flags: `bootstrap/README.md`.
- Declarations: `bootstrap/{packages-fedora.txt,directories.json,repositories.json,links.json}`.
- Application-specific setup: `bin/setup-copyq`; system recipe: `bootstrap/setup.py`.
- Read-only inventory: `python3 bootstrap/audit.py`; known gaps: `bootstrap/AUDIT.md`.
- Earlier snapshot recovery: `~/dev/personal/automation/personal-scripts/workspace/restore-workspace.sh`.
  That tool restores old commits; do not mistake it for the current machine installer.

Read the relevant declarations and inspect Git status/diffs before changing them.
Preserve existing uncommitted work. Follow the appropriate Kanata, systemd, or
personal-skill workflow too when changing those components.

## Classify and finish the change

- **App, shell, editor, keyboard settings:** edit canonical dotfiles and deploy
  the live link. For GUI-managed settings, add an idempotent API/import recipe
  that preserves unrelated settings rather than blindly copying the whole
  application's profile. Include it in the installer. CopyQ's rule is an example.
- **Tool/package:** declare direct dependencies and a repeatable install recipe.
  Use Fedora package names; vendor tools need a maintained version/source and
  validation. Do not treat copying a binary or editing only the current machine
  as installation support. Avoid importing every transitive package on the laptop.
- **Service/autostart:** retain the canonical unit/recipe, dependencies, install
  destination and enable/start behavior. Use `%h` or rendered paths as appropriate.
  Keep device-specific work conditional; never enable every discovered app service
  merely because a unit exists. Apply the systemd/kanata skills for live reloads.
- **Workspace directories:** update `directories.json` for durable grouping or
  non-Git directory structure. Files and datasets still need a real backup.
- **New durable repository:** add destination, clone remote and branch to
  `repositories.json`. Include personal apps, automation, notes and course repos
  the user will want back. Keep existing deliberately chosen backup remotes.
  Exclude disposable experiments, vendor/submodule clones, caches, and incidental
  downloads unless requested. Existing repos must never be pulled, reset, or
  switched by setup. A repo without a remote is a recorded recovery gap, not a
  pretend successful restore. Do not create a remote, upload private contents,
  commit or push without authorization.
- **Ordinary code/content work inside an already listed repo:** no bootstrap
  change is needed unless dependencies, installation, service behavior, or layout
  changed. Repositories are not added again for every source edit.
- **Credentials/runtime state:** do not copy tokens, private keys, browser
  profiles, password databases or clipboard history into dotfiles. Save the
  nonsecret setup recipe and name the authentication/data-restore requirement.

For a broad audit, compare actual configuration links, enabled services, installed
entry points and repositories against declarations. Inspect only the relevant
nonsecret configuration: full app configs can contain private keys. Fix feasible
items and record remaining project/data/hardware prerequisites in `AUDIT.md`.
Do not overwrite a historical recovery manifest or reset repositories to make
an inventory look current.

## Verification and reporting

Keep setup repeatable: back up conflicting live settings; preserve other app
commands/preferences; report failed/pending steps with a nonzero exit status.
Dry-run/check modes must not install, clone, change settings, or start services.
Run focused behavior checks for changed recipes and `install.sh --dry-run`;
use `--check` to report the actual current state. Do not run the entire machine
installer just to test a small app change. A clean-machine claim needs a clean VM
or equivalent test; a successful current-machine check is not proof of that.

For new files, verify they are not ignored and remain in the reviewable diff.
Report live behavior, reproducibility coverage, remaining manual/data steps, and
whether changes are only local, committed, or pushed. Do not imply remote recovery
is ready while required files are uncommitted or unpublished.
