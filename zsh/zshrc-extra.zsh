# this function below is potentially dangerous and shouldnt be used with rm commands
xc() {
    local cmd
    printf -v cmd '%q ' "$@" # build a shell-replayable command line

    {
        printf 'PWD: %s\n' "$PWD"
        printf 'COMMAND: $ %s\n' "$cmd"
        echo
        eval "$cmd" # re-parse → aliases expand
    } | xclip -selection clipboard
}
# activate the py310 conda environment (c a p  )
cap() {
    conda activate py310
}

# Search saved Codex sessions by the time of the last user message.
cs() {
    python3 /home/pt/dev/config/dotfiles/bin/codex-search-sessions.py "$@"
}

alias codex-search-sessions='codex_search_sessions'
