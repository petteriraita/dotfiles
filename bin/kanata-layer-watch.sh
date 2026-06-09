#!/usr/bin/env bash

set -euo pipefail

KANATA_HOST="${KANATA_HOST:-127.0.0.1}"
KANATA_PORT="${KANATA_PORT:-10000}"
DEFAULT_LAYER="${DEFAULT_LAYER:-base}"
GAME_LAYER="${GAME_LAYER:-skyrim}"
GAME_CLASS_REGEX="${GAME_CLASS_REGEX:-steam_proton}"
GAME_TITLE_REGEX="${GAME_TITLE_REGEX:-}"
POLL_INTERVAL="${POLL_INTERVAL:-0.2}"

active_layer=""

send_layer_change() {
    local new_layer="$1"

    if [[ "$new_layer" == "$active_layer" ]]; then
        return
    fi

    printf '{"ChangeLayer":{"new":"%s"}}\n' "$new_layer" | nc -w1 "$KANATA_HOST" "$KANATA_PORT" >/dev/null
    active_layer="$new_layer"
}

detect_layer() {
    local window_id class_line title_line class_value title_value

    window_id="$(xdotool getactivewindow 2>/dev/null || true)"
    if [[ -z "$window_id" ]]; then
        printf '%s\n' "$DEFAULT_LAYER"
        return
    fi

    class_line="$(xprop -id "$window_id" WM_CLASS 2>/dev/null || true)"
    title_line="$(xprop -id "$window_id" _NET_WM_NAME WM_NAME 2>/dev/null || true)"

    class_value="${class_line#*= }"
    title_value="${title_line#*= }"

    if [[ "$class_value" =~ $GAME_CLASS_REGEX ]]; then
        if [[ -z "$GAME_TITLE_REGEX" || "$title_value" =~ $GAME_TITLE_REGEX ]]; then
            printf '%s\n' "$GAME_LAYER"
            return
        fi
    fi

    printf '%s\n' "$DEFAULT_LAYER"
}

wait_for_kanata() {
    until nc -z "$KANATA_HOST" "$KANATA_PORT" 2>/dev/null; do
        sleep 1
    done
}

main() {
    local desired_layer

    wait_for_kanata
    send_layer_change "$DEFAULT_LAYER"

    while true; do
        desired_layer="$(detect_layer)"
        send_layer_change "$desired_layer"
        sleep "$POLL_INTERVAL"
    done
}

main "$@"
