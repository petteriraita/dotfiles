#!/usr/bin/env bash
# Run on DeltaAI with this folder beside the actual personal nvim/ tree.
set -euo pipefail
config_source=$(cd -- "$(dirname -- "$0")" && pwd)
[[ $(uname -m) == aarch64 ]] || { echo 'This installer targets DeltaAI ARM64.' >&2; exit 1; }
[[ -f "$config_source/../nvim/init.lua" ]] || { echo 'Missing personal nvim configuration.' >&2; exit 1; }
version=0.11.5
expected=ea4f9a31b11cc1477ff014aebb7b207684e7280f94ffa97abdab6cacd9b98519
prefix="$HOME/.local/opt/nvim-$version"
mkdir -p "$HOME/.local/bin" "$HOME/.local/opt" "$HOME/.config/deltaai/backups"
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
if [[ ! -x "$prefix/bin/nvim" ]]; then
  curl --fail --location --retry 2 --connect-timeout 15 --max-time 180 \
    -o "$stage/nvim.tar.gz" "https://github.com/neovim/neovim/releases/download/v$version/nvim-linux-arm64.tar.gz"
  printf '%s  %s\n' "$expected" "$stage/nvim.tar.gz" | sha256sum --check
  tar -xzf "$stage/nvim.tar.gz" -C "$stage"
  "$stage/nvim-linux-arm64/bin/nvim" --version
  mv "$stage/nvim-linux-arm64" "$prefix"
fi
backup="$HOME/.config/deltaai/backups/nvim-$(date +%Y%m%dT%H%M%S)-$$"
mkdir -p "$backup"
for target in "$HOME/.local/bin/nvim" "$HOME/.config/nvim"; do
  if [[ -e "$target" || -L "$target" ]]; then
    mv "$target" "$backup/$(basename "$target")-$(basename "$(dirname "$target")")"
  fi
done
ln -s "$prefix/bin/nvim" "$HOME/.local/bin/nvim"
cp -a "$config_source/../nvim" "$HOME/.config/nvim"
export PATH="$HOME/.local/bin:$PATH"
plugin_log="$HOME/.config/deltaai/nvim-plugin-install.log"
if ! timeout 300 "$prefix/bin/nvim" --headless '+Lazy! restore' +qa >"$plugin_log" 2>&1; then
  printf 'Plugin restore failed or timed out; see %s\n' "$plugin_log" >&2
  exit 1
fi
printf 'Personal Neovim config installed; backups: %s\n' "$backup"
"$HOME/.local/bin/nvim" --version | head -n 3
