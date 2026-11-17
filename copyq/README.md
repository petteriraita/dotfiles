# CopyQ setup

Install CopyQ, start it in your desktop session, then run:

```sh
python3 ~/dev/config/dotfiles/bin/setup-copyq
```

The workstation `../install.sh` runs this recipe automatically after installing CopyQ.
It also restores the Alt+V toggle and selected clipboard preferences.
It enables saving all secret clipboard content, including KeePassXC passwords,
in CopyQ history. History is unencrypted unless CopyQ encryption is configured.
The command can be run repeatedly and preserves other CopyQ commands.

Only the setup code belongs in Git; clipboard history and passwords stay local.
The rule is named “Store secret clipboard content” in CopyQ's Commands dialog.
Remove that rule to restore CopyQ's default handling of secret content.
