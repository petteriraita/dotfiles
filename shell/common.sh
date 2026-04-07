# ===== interactive shell helpers =====
# Target shells: zsh, bash

# editors
export EDITOR=nvim
export VISUAL=nvim
export FCEDIT=nvim

# pager behavior
export LESS='-j4'

### add the paths as a set, such that zsh rc reloads dont add duplicate paths
typeset -U path

path=(
    $HOME/.local/bin
    /var/lib/flatpak/exports/bin
    $HOME/.cargo/bin
    $HOME/opt/Isabelle2025-2/bin
    $HOME/.npm-global/bin
    $HOME/.dotnet/tools
    $path
)
# cd into a file starting from root (R)
cdrh() {
    local element
    element=$(
        fd -H -t f -t d . / 2>/dev/null |
            fzf --preview 'bat --style=numbers --color=always {}'
    ) || return

    if [[ -d "$element" ]]; then
        cd "$element"
    else
        cd "$(dirname "$element")"
    fi
}

# cd into a file starting from root (R)
cdr() {
    local element
    element=$(
        fd -t f -t d . / 2>/dev/null |
            fzf --preview 'bat --style=numbers --color=always {}'
    ) || return

    if [[ -d "$element" ]]; then
        cd "$element"
    else
        cd "$(dirname "$element")"
    fi
}

# cd into a file starting from the local directory that you are in right now
cdl() {
    local element
    element=$(
        fd -t f -t d . . 2>/dev/null |
            fzf --preview 'bat --style=numbers --color=always {}'
    ) || return

    if [[ -d "$element" ]]; then
        cd "$element"
    else
        cd "$(dirname "$element")"
    fi
}

balias() {
    "$EDITOR" ~/.bash_aliases
}

iconf() {
    "$EDITOR" ~/.config/i3/config
}

ag() {
    # $@ = all arguments as separate words (correct quoting semantics).
    antigravity "$@"
}

templ() {
    cp -i "$HOME/dev/latex-templates/main.tex" "$1"
    echo "created $1"
}

balias() {
    "$EDITOR" ~/.bash_aliases
}

iconf() {
    "$EDITOR" ~/.config/i3/config
}

md2pdf() {
    pandoc "$1" -o "${1%.md}.pdf" --pdf-engine=xelatex -V fontsize=12pt
}

s() {
    # so if you need to pass the page options etc. use this function
    sioyek "$@" >/dev/null 2>&1 &
    disown
}
x() {
    case $# in
    # 0) echo "got the input of 0 args" ;;
    # 1) echo "got the input of 1 args" ;;
    0)
        xdg-open "$PWD" >/dev/null 2>&1 &
        disown
        ;;
    *)
        # so if there are multiple arguments, all of them are passed to the xdg-open like normally.
        xdg-open "$@" >/dev/null 2>&1 &
        disown
        ;;
    # *) echo "wrong number >= 2 arguments provided to function x" ;;
    esac
}

# activate the py310 conda environment (c a p  )
cap() {
    conda activate py310
}

b() {
    "$EDITOR" "/home/pt/dev/dotfiles/shell/common.sh" # Reload .bashrc to apply changes
}

clip() {
    if [[ -n "$1" ]]; then
        cat "$1"
    else
        cat
    fi | xclip -selection clipboard
}

g() {
    # check if the argument length is 0, then just move to where we are
    if [ -z "$1" ]; then
        abs="$(pwd)"
    else
        abs="$(realpath "$1")" || return 1
    fi

    if [ -f "$abs" ]; then
        cd "$(dirname "$abs")"
    else
        cd "$abs"
    fi
}

p() {
    if [ -z "$1" ]; then
        abs="$(pwd)"
    else
        abs="$(realpath "$1")" || return 1
    fi

    echo -n "$abs" | xclip -selection clipboard
    echo "copied $abs"
}

# MY OWN SETTINGS
#
# CLI TOOLS
alias ..='cd ..'     # Move up one directory level
alias ...='cd ../..' # Move up two directory levels
# making sudo work with aliases
alias sudo='sudo '

# Shell utilitiees
alias ll="ls -lh"
alias ls="ls --color=auto"
alias lla="ls -lha"
alias la="ls -A"
alias lt="ls -lhtr"
alias ld="ls -d */"

### my own ones
alias v="nvim"

alias c='xclip -selection clipboard'

alias zsource='source /home/pt/.config/zsh/zshrc' # Reload .bashrc to apply changes
alias hist='history | sort -r | head -n 10'
alias calc='code /home/petteri/development_files/python_gre/calulator.ipynb'
alias jpamb='code development_files/dtu/program_analysis/jpamb/'
alias py='python3'
alias ca='conda activate'

## GIT
alias gs='git status'
alias ga='git add'
alias gp='git push'
alias gc='git commit -m'
alias gb='git branch'
alias gba='git branch -a'
alias gr='git restore'

alias copywd='pwd | xclip -selection clipboard'
alias ch='code --reuse-window'
