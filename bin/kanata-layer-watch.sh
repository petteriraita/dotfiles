#!/usr/bin/env bash

set -euo pipefail

KANATA_HOST="${KANATA_HOST:-127.0.0.1}"
KANATA_PORT="${KANATA_PORT:-10000}"
DEFAULT_LAYER="${DEFAULT_LAYER:-base}"
GAME_LAYER="${GAME_LAYER:-skyrim}"
GAME_CLASS_REGEX="${GAME_CLASS_REGEX:-steam_proton}"
GAME_TITLE_REGEX="${GAME_TITLE_REGEX:-}"
SIOYEK_LAYER="${SIOYEK_LAYER:-sioyek}"
SIOYEK_CLASS_REGEX="${SIOYEK_CLASS_REGEX:-sioyek}"
POLL_INTERVAL="${POLL_INTERVAL:-0.2}"
LOG_PREFIX="${LOG_PREFIX:-kanata-layer-watch}"

active_layer=""

log() {
    printf '%s: %s\n' "$LOG_PREFIX" "$*" >&2
}

send_layer_change() {
    local new_layer="$1"

    if [[ "$new_layer" == "$active_layer" ]]; then
        return
    fi

    printf '{"ChangeLayer":{"new":"%s"}}\n' "$new_layer" | nc --send-only -w1 "$KANATA_HOST" "$KANATA_PORT" >/dev/null
    log "changed layer to '$new_layer'"
    active_layer="$new_layer"
}

get_active_window_id() {
    local root_line window_id

    root_line="$(xprop -root _NET_ACTIVE_WINDOW 2>/dev/null || true)"
    window_id="$(printf '%s\n' "$root_line" | sed -n 's/.*window id # \(0x[0-9a-fA-F]\+\).*/\1/p')"

    if [[ -n "$window_id" && "$window_id" != "0x0" ]]; then
        printf '%s\n' "$window_id"
        return
    fi

    xdotool getactivewindow 2>/dev/null || true
}

detect_layer() {
    local window_id class_line title_line title_fallback_line class_value title_value desired_layer

    window_id="$(get_active_window_id)"
    if [[ -z "$window_id" ]]; then
        printf '%s\n' "$DEFAULT_LAYER"
        return
    fi

    class_line="$(xprop -id "$window_id" WM_CLASS 2>/dev/null || true)"
    class_value="${class_line#*= }"
    desired_layer="$DEFAULT_LAYER"

    if [[ "$class_value" =~ $SIOYEK_CLASS_REGEX ]]; then
        desired_layer="$SIOYEK_LAYER"
    elif [[ "$class_value" =~ $GAME_CLASS_REGEX ]]; then
        if [[ -z "$GAME_TITLE_REGEX" ]]; then
            desired_layer="$GAME_LAYER"
        else
            title_line="$(xprop -id "$window_id" _NET_WM_NAME 2>/dev/null || true)"
            title_fallback_line="$(xprop -id "$window_id" WM_NAME 2>/dev/null || true)"
            title_value="${title_line#*= }"
            if [[ -z "$title_value" || "$title_value" == "$title_line" ]]; then
                title_value="${title_fallback_line#*= }"
            fi
            [[ "$title_value" =~ $GAME_TITLE_REGEX ]] && desired_layer="$GAME_LAYER"
        fi
    fi

    printf '%s\n' "$desired_layer"
}

wait_for_kanata() {
    until nc -z "$KANATA_HOST" "$KANATA_PORT" 2>/dev/null; do
        sleep 1
    done
}

main() {
    local desired_layer

    log "starting with DISPLAY='${DISPLAY:-}' XAUTHORITY='${XAUTHORITY:-}' port='$KANATA_PORT' game_class_regex='$GAME_CLASS_REGEX' sioyek_class_regex='$SIOYEK_CLASS_REGEX'"
    wait_for_kanata
    send_layer_change "$DEFAULT_LAYER"

    while true; do
        desired_layer="$(detect_layer)"
        send_layer_change "$desired_layer"
        sleep "$POLL_INTERVAL"
    done
}

main "$@"
