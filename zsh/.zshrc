# this is just an empty no-use file to stop the wizard
# # ~/.config/zsh/.zshrc
source ~/.config/zsh/zshrc


# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/home/pt/miniconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/home/pt/miniconda3/etc/profile.d/conda.sh" ]; then
        . "/home/pt/miniconda3/etc/profile.d/conda.sh"
    else
        export PATH="/home/pt/miniconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

