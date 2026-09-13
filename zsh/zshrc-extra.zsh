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

# Search the readable text in saved Codex sessions.
#
# Plain terms are fixed strings.  Use -r/--regex, or a quoted /pattern/, for a
# ripgrep regular expression.
cs() {
    local mode=fixed term sessions_root file text sid session_ts session_ts_pretty matches
    local slash_regex=1
    local -a rg_args

    case "${1:-}" in
        -h|--help)
            cat <<'EOF'
Usage: cs [OPTIONS] SEARCH...

Search the user/assistant text in saved Codex sessions (case-insensitive).

  cs exact words              literal search; quoting is optional
  cs -r 'words? [0-9]+'       regular expression
  cs '/words? [0-9]+/'        regular expression, Obsidian-style

Options:
  -r, --regex   treat SEARCH as a ripgrep regular expression
  -F, --fixed   treat SEARCH as a literal string (the default)
  -h, --help    show this help

Quote regexes so the shell does not interpret characters such as *, |, or ().
EOF
            return 0
            ;;
        -r|--regex)
            mode=regex
            shift
            ;;
        -F|--fixed)
            slash_regex=0
            shift
            ;;
        --)
            shift
            ;;
        -*)
            printf 'cs: unknown option: %s\nTry cs --help for usage.\n' "$1" >&2
            return 2
            ;;
    esac

    (( $# )) || {
        printf 'cs: missing search term\nTry cs --help for usage.\n' >&2
        return 2
    }

    term="$*"

    # A quoted /pattern/ is a convenient shorthand for --regex. An explicit
    # --fixed keeps the slashes literal when that is what the caller wants.
    if [[ "$mode" == fixed && $slash_regex == 1 && "$term" == /*/ && ${#term} -ge 2 ]]; then
        mode=regex
        term="${term[2,-2]}"
    fi

    sessions_root="${CODEX_HOME:-$HOME/.codex}/sessions"

    [[ -d "$sessions_root" ]] || {
        printf 'codex-search-sessions: sessions dir not found: %s\n' "$sessions_root" >&2
        return 1
    }

    rg_args=(--color=always -n -i -C 2 -m 2)
    [[ "$mode" == fixed ]] && rg_args+=(-F)

    # Validate a regex once so a typo is reported once, rather than once per
    # session file. A valid expression returns 1 here because /dev/null is empty.
    if [[ "$mode" == regex ]]; then
        rg -q -- "$term" /dev/null
        (( $? == 2 )) && return 2
    fi

    while IFS= read -r -d '' file; do
        text="$(
            jq -r '
        if .type == "response_item" and .payload.type == "message" and (.payload.role == "user" or .payload.role == "assistant") then
          .payload.content[]? |
          if .type == "input_text" or .type == "output_text" or .type == "text" then
            .text // empty
          else
            empty
          end
        else
          empty
        end
      ' "$file" 2>/dev/null | sed -E '
        /^# AGENTS\.md instructions for /d
        /^<INSTRUCTIONS>$/d
        /^<\/INSTRUCTIONS>$/d
        /^<environment_context>$/d
        /^<\/environment_context>$/d
        /^  <(cwd|shell|current_date|timezone)>.*<\/(cwd|shell|current_date|timezone)>$/d
      '
        )"

        [[ -n "$text" ]] || continue
        matches="$(printf '%s\n' "$text" | rg "${rg_args[@]}" -- "$term")"
        [[ -n "$matches" ]] || continue

        sid="$(
            jq -r '
        select(.type == "session_meta") |
        .payload.id // empty
      ' "$file" 2>/dev/null | head -n 1
        )"

        session_ts="$(
            jq -r '
        select(.type == "session_meta") |
        .payload.timestamp // .timestamp // empty
      ' "$file" 2>/dev/null | head -n 1
        )"

        if [[ -n "$session_ts" ]]; then
            session_ts_pretty="$(TZ="${TZ:-Europe/Copenhagen}" date -d "$session_ts" '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null)"
        else
            session_ts_pretty=''
        fi

        [[ -n "$sid" ]] || sid="${file:t:r}"
        sid="${sid#session-}"
        sid="${sid#rollout-}"

        printf '\n\033[1;36mcodexa %s\033[0m\n' "$sid"
        [[ -n "$session_ts_pretty" ]] && printf '\033[2mdate: %s\033[0m\n' "$session_ts_pretty"
        printf '\033[2mfile: %s\033[0m\n' "$file"
        printf '%s\n' "$matches"
    done < <(fd -0 -t f '\.jsonl$' "$sessions_root" | sort -z -r)
}

alias codex-search-sessions='codex_search_sessions'
