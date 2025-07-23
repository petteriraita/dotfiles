# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac


# setting vim as the default for bash
export FCEDIT=vim
export EDITOR=vim
export VISUAL=vim

export os="/home/petteri/development_files/iitb_courses/os_course/"
export cv="/home/petteri/onedrive_windows/01_projects/work_application_2025/"
export grades="/home/petteri/onedrive_windows/03_resources/grades"
export damp="/home/petteri/onedrive_windows/01_projects/iitb_courses/DAMP_resources/"
export leet="/home/petteri/development_files/iitb_courses/DAA/leetcode/"
export mom="/home/petteri/onedrive_windows/04_archives/mom-help-execl"

export pro="/home/petteri/onedrive_windows/01_projects/"
export courses="/home/petteri/onedrive_windows/04_archives/courses"
export fullstack="/home/petteri/development_files/fullstack/part2/"
export obs="/home/petteri/onedrive_windows/03_resources/Obsidian/my_vault"


# opens up the fullstack project in the proper directory
cfs() {
	if [[ $# -lt 1 ]]; then
		echo "Usage cfs <partnumber> [cursoride flags]"
		return 1
	fi

	local num="$1"
	# deleting the $1 from the arguments such that $@ will return the rest of the args
	shift

	base="/home/petteri/development_files/fullstack/part$num"
	cursor "$base" "$@"
}


md2pdf() {
    pandoc "$1" -o "${1%.md}.pdf" --pdf-engine=xelatex -V fontsize=12pt 
}
coffre() {
    cd /home/petteri/development_files/iitb_courses/IPL/coffre && ./qemu-coffre-linux-x86_64-NEW ../qcow/petteri.amd64.new.qcow2 4 4G
}
x() {
	xdg-open "${1:-.}" &> /dev/null
}

## NOTE THIS DOESN'T WORK. DOES NOT COPY...
# in this command, fc -ln picks up the previous command that was run before it
# | sed 's/^[[:space:]]*//'   ==> this command takes the stdin of the fc -ln command and trims the whitespace that exists in the beginning of the command
# c() {
# 	cmd="$(fc -ln -1| sed 's/^[[:space:]]*//')"
# 	# this part runs the command and redirects the stdcmd to clipboard (if you wanted to copy the command you would just echo it)
# 	printf %s "$cmd" | xclip -selection clipboard -loops 1
# 	echo "✔ previous output copied"
# }


clip() {
	"$@" | tee >(xclip -selection clipboard)
	echo "copied to clipboard"
}



psfilter() {
    if [ $# -eq 0 ]; then
        echo "Usage: psfilter <pattern>"
        return 1
    fi
    ps aux | awk -v pattern="$1" 'NR==1 || $0 ~ pattern'
}



# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
	# We have color support; assume it's compliant with Ecma-48
	# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
	# a case would tend to support setf rather than setaf.)
	color_prompt=yes
    else
	color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi


# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi
# increasing the scroll speed
# imwheel -k -b "4 5" &

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/home/petteri/Downloads/yes/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/home/petteri/Downloads/yes/etc/profile.d/conda.sh" ]; then
        . "/home/petteri/Downloads/yes/etc/profile.d/conda.sh"
    else
        export PATH="/home/petteri/Downloads/yes/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

cursor() { /opt/cursor.appimage --no-sandbox "$@" >/dev/null 2>&1 & }
manall() { man -a "$1" | less; }
export PATH=~/.npm-global/bin:$PATH
