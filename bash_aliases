# MY OWN SETTINGS 
alias ..='cd ..'                                    # Move up one directory level
alias ...='cd ../..'                                # Move up two directory levels
alias update='sudo apt update && sudo apt upgrade'  # Update and upgrade packages
alias bsource='source ~/.bashrc'                     # Reload .bashrc to apply changes
alias b='vim ~/.bashrc'                     # Reload .bashrc to apply changes
alias balias='vim ~/.bash_aliases'                     # Reload .bashrc to apply changes
alias coderc='code ~/.bashrc'
alias hist='history | sort -r | head -n 10'
alias calc='code /home/petteri/development_files/python_gre/calulator.ipynb'
alias jpamb='code development_files/dtu/program_analysis/jpamb/'
alias gowin='cd /mnt/c/Users/Lanlan/Documents/Petteri-Raita-2025-files'
alias py='python3'

# the JPAMB project
alias ia="uv run framework/integrated_analysis.py"
alias sa="uv run framework/static_analysis.py"


alias night='redshift -O 1000'
alias day='redshift -x'
alias eve='redshift -O 2700'


alias gs='git status'
alias ga='git add'
alias gc='git commit -m'

alias xopen='xdg-open'
alias copywd='pwd | xclip -selection clipboard'
alias ch='code --reuse-window'
alias c='code .'

# Shell utilitiees
alias ll='ls -l'

