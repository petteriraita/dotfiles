# ===== interactive shell helpers =====
# Target shells: zsh, bash

# editors
export EDITOR=nvim
export VISUAL=nvim
export FCEDIT=nvim

# pager behavior
export LESS='-j4'

# Workspace layout. Keep project paths derived from this small set of roots so
# a future reorganization changes one place rather than many shell helpers.
export DEV_ROOT="${DEV_ROOT:-$HOME/dev}"
export DEV_CONFIG="${DEV_CONFIG:-$DEV_ROOT/config/dotfiles}"
export DEV_PERSONAL="${DEV_PERSONAL:-$DEV_ROOT/personal}"
export DEV_SCHOOL="${DEV_SCHOOL:-$DEV_ROOT/school}"
export DEV_DTU_SPRING_2026="${DEV_DTU_SPRING_2026:-$DEV_SCHOOL/dtu/2026-spring}"
export PTT_ROOT="${PTT_ROOT:-$DEV_PERSONAL/apps/push-to-talk}"
export LATEX_TEMPLATES="${LATEX_TEMPLATES:-$DEV_PERSONAL/learning/latex-templates}"
export OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-$DEV_PERSONAL/knowledge/obsidian_vault}"

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
    cp -i "$LATEX_TEMPLATES/main.tex" "$1"
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

# s() {
#     # so if you need to pass the page options etc. use this function
#     sioyek "$@" >/dev/null 2>&1 &
#     disown
# }
# nvim quick opener. If no args, open in the CWD
v() {
    case $# in
    0)
        nvim "$PWD"
        ;;
    *)
        nvim "$@"
        ;;
    esac
}
x() {
    local target mime handler
    local -a editor_files=()

    if [ "$#" -eq 0 ]; then
        set -- "$PWD"
    fi

    for target in "$@"; do
        # Use an absolute path so filenames beginning with '-' stay filenames.
        if [ -f "$target" ]; then
            case "$target" in
                /*) ;;
                *) target="$PWD/$target" ;;
            esac
            mime=$(xdg-mime query filetype "$target" 2>/dev/null)
            handler=$(xdg-mime query default "$mime" 2>/dev/null)
            if [ "$handler" = "nvim.desktop" ]; then
                editor_files+=("$target")
                continue
            fi
        fi
        xdg-open "$target" >/dev/null 2>&1 &
        disown
    done

    if [ "${#editor_files[@]}" -gt 0 ]; then
        nvim -- "${editor_files[@]}"
    fi
}

# activate the py310 conda environment (c a p  )
cap() {
    conda activate py310
}

b() {
    "$EDITOR" "$DEV_CONFIG/shell/common.sh" # Reload .bashrc to apply changes
}

clip() {
    if [[ -n "$1" ]]; then
        cat "$1"
    else
        cat
    fi | xclip -selection clipboard
}

g() {
    local target

    if [ "$#" -gt 1 ]; then
        printf 'g: expected at most one path\n' >&2
        return 2
    fi

    target=${1:-"$PWD"}

    if [ -f "$target" ] || { [ -L "$target" ] && [ ! -d "$target" ]; }; then
        cd -- "$(dirname -- "$target")"
    else
        cd -- "$target"
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

_codexa() {
    local use_home=$1
    local use_search=$2
    local subcommand
    local -a options
    shift 2

    options=(--dangerously-bypass-approvals-and-sandbox)
    if [ "$use_home" = true ]; then
        options+=(-C /home/pt)
    fi
    if [ "$use_search" = true ]; then
        options+=(--search)
    fi

    if [ "$#" -eq 0 ]; then
        command codex "${options[@]}"
        return
    fi

    case $1 in
    resume | fork)
        subcommand=$1
        shift
        ;;
    *)
        subcommand=resume
        ;;
    esac

    command codex "$subcommand" "${options[@]}" "$@"
}

# Full home-directory access; optionally resume the supplied session ID.
codexa() {
    _codexa true false "$@"
}

# Full home-directory access with web search.
codexas() {
    _codexa true true "$@"
}

# Full access rooted in the current directory.
codexal() {
    _codexa false false "$@"
}

# Full access rooted in the current directory, with web search.
codexasl() {
    _codexa false true "$@"
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

alias vn="nvim"

### my own ones
alias c='xclip -selection clipboard'

alias zsource='source /home/pt/.config/zsh/zshrc' # Reload .bashrc to apply changes
alias hist='history | sort -r | head -n 10'
alias calc='code /home/petteri/development_files/python_gre/calulator.ipynb'
alias jpamb='code development_files/dtu/program_analysis/jpamb/'
alias py='python3'
alias ca='conda activate'
alias thyconvert="$DEV_DTU_SPRING_2026/02256_Automated_Reasoning/converter.py"

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
