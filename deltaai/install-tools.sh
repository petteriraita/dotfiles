#!/usr/bin/env bash
# Official prebuilt ARM64 binaries; no root or cluster compilation needed.
set -euo pipefail
[[ $(uname -m) == aarch64 ]] || { echo 'This installer targets DeltaAI ARM64.' >&2; exit 1; }
setup_dir=$(mktemp -d)
trap 'rm -rf -- "$setup_dir"' EXIT
mkdir -p "$HOME/.local/bin" "$HOME/.config/deltaai/backups"
install_tool() {
  local name=$1 url=$2 expected=$3 archive=$4
  curl --fail --location --retry 2 --connect-timeout 15 --max-time 120 \
    --output "$setup_dir/$archive.tar.gz" "$url"
  printf '%s  %s\n' "$expected" "$setup_dir/$archive.tar.gz" | sha256sum --check
  tar -xzf "$setup_dir/$archive.tar.gz" -C "$setup_dir" "$archive/$name"
  if [[ -e "$HOME/.local/bin/$name" ]]; then
    cp -p "$HOME/.local/bin/$name" "$HOME/.config/deltaai/backups/$name.$(date +%Y%m%dT%H%M%S).$$"
  fi
  install -m 755 "$setup_dir/$archive/$name" "$HOME/.local/bin/$name"
  "$HOME/.local/bin/$name" --version
}
install_tool rg \
  https://github.com/BurntSushi/ripgrep/releases/download/15.2.0/ripgrep-15.2.0-aarch64-unknown-linux-musl.tar.gz \
  800b1e7206afe799dfb5a6901f23147cfaabe0e52210538100f61e86e1740915 \
  ripgrep-15.2.0-aarch64-unknown-linux-musl
install_tool fd \
  https://github.com/sharkdp/fd/releases/download/v10.5.0/fd-v10.5.0-aarch64-unknown-linux-musl.tar.gz \
  d76c4317f7d5dba69f8a2a15856c90c777e7f0dd4e85f0de8c76de6992c374d4 \
  fd-v10.5.0-aarch64-unknown-linux-musl
