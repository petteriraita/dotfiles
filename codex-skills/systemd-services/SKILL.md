---
name: systemd-services
description: Create, update, enable, or troubleshoot the user's Fedora systemd services, keeping canonical unit files in their tracked dotfiles repository.
---

# Systemd Services

Use this skill for local systemd service or timer work on this Fedora laptop.

## Canonical files

- User-unit sources belong in `/home/pt/dev/config/dotfiles/systemd/user/`.
- System-unit sources belong in `/home/pt/dev/config/dotfiles/systemd/system/` only when root-level access is actually required.
- Do not create or edit a regular unit file directly in `~/.config/systemd/user/`. Create or edit the canonical dotfiles source, then make the live user-unit path a symlink to it.

## User services

Prefer a user service for per-user local applications, dashboards, automation, and SSH tunnels. Use explicit absolute paths for `WorkingDirectory` and `ExecStart`. For a local web application, bind to `127.0.0.1` unless the user explicitly requests LAN access.

After changing a user unit:

1. Validate the source with `systemd-analyze --user verify` when applicable.
2. Run `systemctl --user daemon-reload`.
3. Enable it with `systemctl --user enable <unit>` when it should start automatically.
4. Start or restart it, then verify status and the relevant endpoint or observable behavior.

Check `loginctl show-user pt -p Linger` when the service must run without an active graphical login. Do not enable lingering or alter root-managed services without user authorization.

## Deployment and safety

Before replacing an existing live unit with a symlink, inspect it and confirm it matches the intended source. Preserve unrelated service files and existing user changes. Root-level units require separate installation to `/etc/systemd/system/` and any necessary administrator authentication; do not restart `systemd-logind` merely to apply a `logind.conf` change—reboot instead.
