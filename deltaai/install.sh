#!/usr/bin/env bash
set -euo pipefail
config_source=$(cd -- "$(dirname -- "$0")" && pwd)
backup_dir="$HOME/.config/deltaai/backups/$(date +%Y%m%dT%H%M%S)-$$"
mkdir -p "$backup_dir" "$HOME/.config/deltaai" "$HOME/.terminfo"
for config in .bashrc .zshrc; do
  if [[ -f "$HOME/$config" ]]; then
    cp -p "$HOME/$config" "$backup_dir/$config"
  fi
done
cp "$config_source/zshrc.zsh" "$HOME/.config/deltaai/zshrc.zsh"
tic -x -o "$HOME/.terminfo" "$config_source/tmux-256color.terminfo"
if ! grep -Fq '# Personal DeltaAI Zsh setup' "$HOME/.zshrc"; then
  cat >> "$HOME/.zshrc" <<'ZSH'

# Personal DeltaAI Zsh setup
source "$HOME/.config/deltaai/zshrc.zsh"
ZSH
fi
if ! grep -Fq '# Personal DeltaAI interactive shell' "$HOME/.bashrc"; then
  cat >> "$HOME/.bashrc" <<'BASH'

# Personal DeltaAI interactive shell
# Preserve noninteractive commands, transfers, and batch jobs.
if [[ $- == *i* && -n ${SSH_TTY:-} && -z ${ZSH_VERSION:-} ]]; then
    if command -v zsh >/dev/null 2>&1; then
        exec zsh
    fi
fi
BASH
fi
printf 'Installed DeltaAI shell config. Backups: %s\n' "$backup_dir"
