# this function below is potentially dangerous and shouldnt be used with rm commands
xc() {
  local cmd
  printf -v cmd '%q ' "$@"   # build a shell-replayable command line

  {
    printf 'PWD: %s\n' "$PWD"
    printf 'COMMAND: $ %s\n' "$cmd"
    echo
    eval "$cmd"              # re-parse → aliases expand
  } | xclip -selection clipboard
}
# activate the py310 conda environment (c a p  )
cap() {
	conda activate py310
}

codex_search_sessions() {
  local term sessions_root file text sid session_ts session_ts_pretty matches
  term="${1:?usage: codex-search-sessions SEARCH_TERM}"
  sessions_root="${CODEX_HOME:-$HOME/.codex}/sessions"

  [[ -d "$sessions_root" ]] || {
    printf 'codex-search-sessions: sessions dir not found: %s\n' "$sessions_root" >&2
    return 1
  }

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
    matches="$(printf '%s\n' "$text" | rg --color=always -n -i -C 2 -m 2 -- "$term")"
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

    printf '\n\033[1;36mcodex resume %s\033[0m\n' "$sid"
    [[ -n "$session_ts_pretty" ]] && printf '\033[2mdate: %s\033[0m\n' "$session_ts_pretty"
    printf '\033[2mfile: %s\033[0m\n' "$file"
    printf '%s\n' "$matches"
  done < <(fd -0 -t f '\.jsonl$' "$sessions_root" | sort -z -r)
}

alias codex-search-sessions='codex_search_sessions'
