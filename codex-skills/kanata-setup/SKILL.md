---
name: kanata-setup
description: Change, test, reload, or troubleshoot the user's Kanata keyboard configuration and its per-application layers on Fedora/i3/X11. Use for Kanata mappings, tap-hold behavior, device selection, the Skyrim or Sioyek layers, the layer watcher, and Kanata systemd services; not for unrelated keyboard shortcuts handled only by i3 or an application.
---

# Kanata Setup

Work against the current setup in `/home/pt/dev/dotfiles`; do not reconstruct it from old chat examples.

## Current architecture

- Main config: `/home/pt/dev/dotfiles/kanata/config.kbd`
- Known fallback config: `/home/pt/dev/dotfiles/kanata/safe.kbd`; do not overwrite it casually.
- Root service source: `/home/pt/dev/dotfiles/systemd/system/kanata.service`
- Installed root unit: `/etc/systemd/system/kanata.service`
- Focus watcher: `/home/pt/dev/dotfiles/bin/kanata-layer-watch.sh`
- User service: `/home/pt/dev/dotfiles/systemd/user/kanata-layer-watch.service`, symlinked from `/home/pt/.config/systemd/user/kanata-layer-watch.service`
- Narrow sudo rules source: `/home/pt/dev/dotfiles/systemd/sudoers.d/codex-kanata`

Kanata runs as the system service and exposes its layer-control server on port 10000. The user watcher reads the focused X11 window and selects `base`, `skyrim`, or `sioyek`. Skyrim uses plain gaming keys. Sioyek stays close to `base` but makes `j` plain and repeatable. Page Up/Down emit virtual keys used by the push-to-talk setup; preserve those positions across layers unless the user asks to change them.

## Before editing

1. Read every file relevant to the requested behavior and inspect `git status` and `git diff` for those files. Existing dirty changes belong to the user.
2. Inspect the live unit definitions and status when service behavior matters. Do not assume a dotfiles file is installed or symlinked; verify with `systemctl cat`, `readlink`, or `cmp`.
3. For an application-specific layer, inspect its real `WM_CLASS` and title with `xprop`. Do not guess them from the application name.
4. Identify the smallest behavior change the user asked for. A request to make one key plain in one application does not imply reusing the full `skyrim` layer.

## Editing rules

- Edit canonical dotfiles sources, not symlink destinations or `/etc` copies.
- Keep `defsrc` and every `deflayer` positionally aligned and with the same number of entries.
- Preserve unrelated aliases, devices, layers, tap-hold timings, and push-to-talk fake keys.
- Account for `linux-x11-repeat-delay-rate 9999,1`: home-row tap-hold keys such as `j` will not behave like ordinary repeatable keys when held. Use a narrowly scoped app layer when that is the desired exception.
- The Fedora `nc` is Ncat; layer commands in the watcher need `nc --send-only -w1` so the pipe does not hang waiting for the server.
- Do not broaden an application regex or map an application to a broad layer merely because it fixes one symptom.

## Validate before reload

Always validate the main configuration before restarting anything:

```sh
kanata --check --cfg /home/pt/dev/dotfiles/kanata/config.kbd
```

If the check fails, fix the source and do not restart the live service. For watcher changes, also run:

```sh
bash -n /home/pt/dev/dotfiles/bin/kanata-layer-watch.sh
systemd-analyze --user verify /home/pt/dev/dotfiles/systemd/user/kanata-layer-watch.service
```

## Reload only what changed

- `config.kbd`: restart `kanata.service`, then restart `kanata-layer-watch.service`. The watcher caches its last requested layer, so restarting it after Kanata ensures the active app layer is sent again.
- Watcher script or its user unit: run the user daemon reload only if the unit changed, then restart the watcher.
- Root unit source: install the exact source to `/etc`, run the system daemon reload, restart Kanata, then restart the watcher.

Use the configured narrow sudo commands when available:

```sh
sudo -n systemctl restart kanata.service
systemctl --user restart kanata-layer-watch.service
```

For a changed root unit:

```sh
sudo -n install -m 644 /home/pt/dev/dotfiles/systemd/system/kanata.service /etc/systemd/system/kanata.service
sudo -n systemctl daemon-reload
sudo -n systemctl restart kanata.service
systemctl --user restart kanata-layer-watch.service
```

Do not claim success from a successful config check or restart alone. Verify both services are active, inspect their recent journal output, and test the requested key behavior in the target application. If input becomes unsafe or unusable, stop further restarts and use the known fallback deliberately rather than overwriting the main config.

## Lessons from previous failures

- Reusing the entire Skyrim layer for Sioyek changed much more than the requested `j` behavior.
- Restarting or reloading the wrong system/user unit left source changes unapplied.
- Treating copied and symlinked units as interchangeable caused misleading deployment instructions.
- An initial watcher implementation used incompatible `nc` behavior and unreliable active-window detection.
- Restarting Kanata without resetting the watcher's cached layer could leave the focused app on the wrong layer.
- Editing first and validating afterward risked breaking the user's primary keyboard.
