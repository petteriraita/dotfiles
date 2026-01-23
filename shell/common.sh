# ===== interactive shell helpers =====
# Target shells: zsh, bash

# editors
export EDITOR=vim
export VISUAL=vim
export FCEDIT=vim

# pager behavior
export LESS='-j4'

# paths
export PATH="$HOME/.local/bin:$PATH"
export PATH="/var/lib/flatpak/exports/bin:$PATH"



cdf() {
  local dir
  dir=$(fd -t f | fzf) || return
  vim "$dir"
}

cdd() {
  local dir
  dir=$(fd -t d | fzf) || return
  cd "$dir"
}


ag() {
 	# $@ = all arguments as separate words (correct quoting semantics).
	antigravity "$@"
}

templ() {
    cp -i "$HOME/dev/latex-templates/main.tex" "$1"
    echo "created $1"
}

md2pdf() {
    pandoc "$1" -o "${1%.md}.pdf" --pdf-engine=xelatex -V fontsize=12pt
}

x() {
	xdg-open "${2:-.}" > /dev/null 2>&1
}
# activate the py310 conda environment (c a p  )
cap() {
	conda activate py310
}


clip() {
    if [[ -n "$1" ]]; then
        cat "$1"
    else
        cat
    fi | xclip -selection clipboard
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
alias ..='cd ..'                                    # Move up one directory level
alias ...='cd ../..'                                # Move up two directory levels
# making sudo work with aliases
alias sudo='sudo '

# Shell utilitiees
alias ll="ls -lh"
alias ls="ls --color=auto"
alias lla="ls -lha"
alias la="ls -A"
alias lt="ls -lhtr"
alias ld="ls -d */"


alias c='xclip -selection clipboard'


alias zsource='source /home/pt/.config/zsh/zshrc'                     # Reload .bashrc to apply changes
alias b='vim "/home/pt/dev/dotfiles/shell/common.sh"'                     # Reload .bashrc to apply changes
alias balias='vim ~/.bash_aliases'                     # Reload .bashrc to apply changes
alias hist='history | sort -r | head -n 10'
alias calc='code /home/petteri/development_files/python_gre/calulator.ipynb'
alias jpamb='code development_files/dtu/program_analysis/jpamb/'
alias py='python3'
alias vim='vimx'


# the JPAMB project
alias ia="uv run framework/integrated_analysis.py"
alias sa="uv run framework/static_analysis.py"


alias night='redshift -O 1000'
alias day='redshift -x'
alias eve='redshift -O 2700'

## i3
alias iconf='vim ~/.config/i3/config'



## GIT
alias gs='git status'
alias ga='git add'
alias gp='git push'
alias gc='git commit -m'
alias gb='git branch'
alias gba='git branch -a'
alias gr='git restore'

alias xopen='xdg-open'
alias copywd='pwd | xclip -selection clipboard'
alias ch='code --reuse-window'





