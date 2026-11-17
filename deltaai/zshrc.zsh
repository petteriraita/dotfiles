# Portable subset of the local Zsh setup for DeltaAI.
typeset -U path
path=($HOME/.local/bin $path)
autoload -Uz colors && colors
PS1='%B%F{red}[%F{magenta}%~%F{red}]%f%b$ '
HISTSIZE=10000
SAVEHIST=10000
HISTFILE=$HOME/.zsh_history
setopt APPEND_HISTORY HIST_IGNORE_DUPS NO_BEEP
zstyle ':completion:*' menu select
zmodload zsh/complist
autoload -Uz compinit
compinit
_comp_options+=(globdots)

bindkey -v
KEYTIMEOUT=10
bindkey -M viins '^?' backward-delete-char
bindkey -M viins '^[.' insert-last-word
for keymap in viins vicmd; do
  bindkey -M "$keymap" '^L' clear-screen
  bindkey -M "$keymap" '^G' edit-command-line
  bindkey -M "$keymap" '^X^E' edit-command-line
done
bindkey -M menuselect h vi-backward-char
bindkey -M menuselect j vi-down-line-or-history
bindkey -M menuselect k vi-up-line-or-history
bindkey -M menuselect l vi-forward-char
autoload -Uz edit-command-line
zle -N edit-command-line

if (( $+commands[nvim] )); then
  export EDITOR=nvim
else
  export EDITOR=vim
fi
export VISUAL=$EDITOR FCEDIT=$EDITOR
export SHELL=${commands[zsh]}
v() { "$EDITOR" "${@:-$PWD}"; }
alias vn='$EDITOR'
alias ..='cd ..'
alias ...='cd ../..'
alias ls='ls --color=auto'
alias ll='ls -lh'
alias lla='ls -lha'
alias la='ls -A'
alias lt='ls -lhtr'
alias ld='ls -d */'
alias py=python3
alias gs='git status'
alias ga='git add'
alias gp='git push'
alias gc='git commit -m'
alias gb='git branch'
alias gba='git branch -a'
alias gr='git restore'
alias zsource='source ~/.zshrc'
alias hist='history | sort -r | head -n 10'
cap() {
  module load python/3.10.14 || return
  source /work/nvme/bfdu/cs444/fa26/mp3/venv/bin/activate
}
b() { "$EDITOR" "$HOME/.config/deltaai/zshrc.zsh"; }
g() {
  if (( $# > 1 )); then
    print -u2 'g: expected at most one path'
    return 2
  fi
  local target=${1:-$PWD}
  if [[ -f $target || ( -L $target && ! -d $target ) ]]; then
    cd -- "${target:h}"
  else
    cd -- "$target"
  fi
}

# OSC 52 reaches the local terminal clipboard through the existing tmux.
clip() {
  local encoded
  if (( $# )); then
    encoded=$(base64 < "$1" | tr -d '\n') || return
  else
    encoded=$(base64 | tr -d '\n') || return
  fi
  case $TERM in
    tmux*|screen*) printf '\033Ptmux;\033\033]52;c;%s\007\033\\' "$encoded" ;;
    *) printf '\033]52;c;%s\007' "$encoded" ;;
  esac
}
alias c=clip
p() { realpath -- "${1:-$PWD}" | tr -d '\n' | clip; }
copywd() { printf %s "$PWD" | clip; }
_delta_yank() { zle .vi-yank; printf %s "$CUTBUFFER" | clip; }
_delta_yank_line() { zle .vi-yank-whole-line; printf %s "$CUTBUFFER" | clip; }
zle -N _delta_yank
zle -N _delta_yank_line
for keymap in vicmd visual; do
  bindkey -M "$keymap" y _delta_yank
  bindkey -M "$keymap" Y _delta_yank_line
done

# Match local cursor shapes and mark prompts for local tmux prompt shortcuts.
zle-keymap-select() {
  case $KEYMAP in
    vicmd) printf '\033[1 q' ;;
    *) printf '\033[5 q' ;;
  esac
}
zle-line-init() { zle -K viins; printf '\033[5 q'; }
zle -N zle-keymap-select
zle -N zle-line-init
autoload -Uz add-zsh-hook
typeset -gi _delta_command_open=0
_delta_precmd() {
  local command_status=$?
  (( _delta_command_open )) && printf '\033]133;D;%d\033\\' "$command_status"
  _delta_command_open=0
}
_delta_preexec() { printf '\033]133;C\033\\'; _delta_command_open=1; }
PS1=$'%{\033]133;A\033\\%}'$PS1
add-zsh-hook precmd _delta_precmd
add-zsh-hook preexec _delta_preexec
