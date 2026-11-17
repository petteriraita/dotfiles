# DeltaAI shell setup

Portable core of the local shell config, installed in `~/.config/deltaai/`.
Run `bash install.sh` on DeltaAI with all three setup files present.
The installer backs up `.bashrc` and `.zshrc` before adding its source hooks.

Interactive SSH sessions start Zsh. Noninteractive commands and batch jobs
retain their normal shell. Includes Vim command editing, Ctrl-G external
editing, Alt-dot, menu completion, common aliases, OSC 52 clipboard helpers,
and OSC 133 markers for the local tmux prompt navigation/copy shortcuts.
The supplied terminfo source fixes missing `tmux-256color` support on DeltaAI.

`install-nvim.sh` installs the official checksum-verified ARM64 Neovim 0.11.5
build into `~/.local/opt` and copies the actual personal `../nvim/` configuration.
This matches the local theme, cursor, mappings and plugin declarations. SSH yanks
use OSC 52 with explicit tmux passthrough; local sessions retain X11 clipboard
handling. Editor puts use the last copied text; paste new laptop text with the
terminal paste shortcut. Plugin binaries/LSP servers still need ARM64 support.
The laptop continues to handle i3/Kitty/tmux bindings and fonts.

From the laptop, deploy the current checked-out configs with:

```sh
python3 ~/dev/config/dotfiles/deltaai/deploy.py
# Equivalent opt-in bootstrap step:
~/dev/config/dotfiles/install.sh --only deltaai
```

This requires DeltaAI SSH/MFA. If a signed-in SSH session is already idle at a
shell prompt in tmux, `deploy.py --tmux-pane SESSION:WINDOW.PANE` can reuse it.
Do not paste into a pane containing a running editor, job or unfinished command.
The deployment backs up remote settings before replacement. Reload the shell
with `source ~/.config/deltaai/zshrc.zsh`, then `v FILE` opens Neovim.
The installer restores the locally locked plugins, logging to
`~/.config/deltaai/nvim-plugin-install.log`. To retry, run
`nvim --headless '+Lazy! restore' +qa`.

`bash install-tools.sh` installs checksum-verified official ARM64 builds of
ripgrep 15.2.0 and fd 10.5.0 into `~/.local/bin`. The portable Zsh config adds
that directory to PATH. `cap` activates the course MP3 Python environment;
it does not allocate GPU resources. `b` edits the portable shell config and
`zsource` reloads it through `~/.zshrc`.
