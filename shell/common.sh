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
	$path
)

cdfv() {
	local file
	file=$(fzf --bind "change:reload:fd -t f {q} /" \
		--preview "bat --style=numbers --color=always {}" \
		--phony \
		--query "") || return
	"$EDITOR" "$file"
}

cdfp() {
	local file
	file=$(fzf --bind "change:reload:fd -t f {q} /" \
		--preview "bat --style=numbers --color=always {}" \
		--phony \
		--query "") || return
	echo "$file"
}

balias() {
	"$EDITOR" ~/.bash_aliases
}

iconf() {
	"$EDITOR" ~/.config/i3/config
}

cdf() {
	local dir
	dir=$(fd -t f . /home | fzf) || return
	"$EDITOR" "$dir"
}

cdd() {
	local dir
	dir=$(fd -t d . /home | fzf) || return
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

balias() {
	"$EDITOR" ~/.bash_aliases
}

iconf() {
	"$EDITOR" ~/.config/i3/config
}

md2pdf() {
	pandoc "$1" -o "${1%.md}.pdf" --pdf-engine=xelatex -V fontsize=12pt
}

x() {
	case $# in
	# 0) echo "got the input of 0 args" ;;
	# 1) echo "got the input of 1 args" ;;
	0)
		xdg-open "$PWD" >/dev/null 2>&1 &
		disown
		;;
	1)
		xdg-open "$1" >/dev/null 2>&1 &
		disown
		;;
	*) echo "wrong number >= 2 arguments provided to function x" ;;
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

# the JPAMB project
alias ia="uv run framework/integrated_analysis.py"
alias sa="uv run framework/static_analysis.py"

alias night='redshift -O 1000'
alias day='redshift -x'
alias eve='redshift -O 2700'

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
