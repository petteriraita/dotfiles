# MY OWN SETTINGS 
#
# CLI TOOLS
alias ..='cd ..'                                    # Move up one directory level
alias ...='cd ../..'                                # Move up two directory levels

# Shell utilitiees
alias ll="ls -lh"
alias ls="ls --color=auto"
alias lla="ls -lha"
alias la="ls -A"
alias lt="ls -lhtr"
alias ld="ls -d */"




alias bsource='source ~/.bashrc'                     # Reload .bashrc to apply changes
alias b='vim ~/.bashrc'                     # Reload .bashrc to apply changes
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


