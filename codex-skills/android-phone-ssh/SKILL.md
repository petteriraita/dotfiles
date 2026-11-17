---
name: android-phone-ssh
description: Connect to the user's Android phone through its existing Termux SSH setup for phone-side tasks and file transfers. Use for requests to change or inspect the phone, not for ordinary phone advice.
---

# Android Phone SSH

The phone has an `android-phone` alias in `/home/pt/.ssh/config`. It uses the phone's Tailscale address and Termux SSH on port 8022. Check the connection before saying the phone is unavailable:

```sh
ssh -F /home/pt/.ssh/config -o BatchMode=yes -o ConnectTimeout=10 android-phone 'printf connected'
```

Use the same `-F /home/pt/.ssh/config` with `scp`. It avoids a local system SSH config ownership error seen in some sessions. The alias contains the host, Termux user, port, and key; do not hardcode or disclose them unnecessarily.

If SSH reports `socket: Operation not permitted`, the current execution environment may be blocking network access before the phone is reached. Do not describe that as a phone or SSH setup failure. Retry in a network-enabled session when available.

For a timeout or refusal, check `tailscale status` and `tailscale ping` for the phone, then retry SSH after any phone-side action. A refusal while Tailscale reaches the phone means Termux `sshd` was not listening at that moment. Since 2026-11-05, `termux-services` supervises `sshd` and Physio Log; `~/.termux/boot/start-services` starts that supervisor after reboot. A laptop SSH tunnel cannot restart Termux when the whole app or boot receiver is stopped. If needed, ask the user to open Termux and run `. "$PREFIX/etc/profile.d/start-services.sh"` once, then retry SSH immediately. If Tailscale shows the phone offline, ask the user to connect Tailscale on the phone. Tailscale provides a network path; file access still needs Termux SSH.

Once SSH succeeds, check `SVDIR="$PREFIX/var/service" sv status sshd physio-log` and the requested phone result. The canonical supervisor setup recipe is `/home/pt/dev/config/dotfiles/bin/setup-physio-phone-services`; do not reinstall it based only on one failed connection. Android can still stop all Termux processes, so never claim that the phone-hosted app has guaranteed availability.

On the phone, `~/storage/downloads` maps to Android Downloads. `termux-open` can launch an Android app for a transferred file. Check phone-side permissions and the observable result before reporting a task complete. In particular, copying a `.vcf` to Downloads or opening the contact importer does **not** prove that the contact was saved. The current `termux-contact-list` needs Android `READ_CONTACTS` permission, and no `termux-contact-add` command is installed. If Android requires a tap to import, state that clearly and ask the user to finish that step.
