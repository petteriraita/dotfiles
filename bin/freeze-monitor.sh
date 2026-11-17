#!/usr/bin/env bash

# Capture enough context to diagnose an intermittent X11/AMDGPU desktop stall
# without adding noticeable load during normal use.

set -u

INTERVAL_SECONDS="${INTERVAL_SECONDS:-2}"
PROBE_TIMEOUT_SECONDS="${PROBE_TIMEOUT_SECONDS:-1}"
FAILURES_BEFORE_SNAPSHOT="${FAILURES_BEFORE_SNAPSHOT:-2}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/freeze-monitor"
LOG_FILE="$STATE_DIR/samples.log"
MAX_LOG_BYTES="${MAX_LOG_BYTES:-20971520}"
DISPLAY="${DISPLAY:-:0}"
XAUTHORITY="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}"
export DISPLAY XAUTHORITY

mkdir -p "$STATE_DIR"

rotate_log_if_needed() {
    local size="0"

    [[ -f "$LOG_FILE" ]] || return 0
    size="$(stat --format='%s' "$LOG_FILE" 2>/dev/null || printf '0')"
    if ((size >= MAX_LOG_BYTES)); then
        mv -f "$LOG_FILE" "$LOG_FILE.1"
    fi
}

log() {
    rotate_log_if_needed
    printf '%s %s\n' "$(date --iso-8601=seconds)" "$*" >>"$LOG_FILE"
}

read_value() {
    local path="$1"

    if [[ -r "$path" ]]; then
        tr '\n' ' ' <"$path" | sed 's/[[:space:]]*$//'
    else
        printf 'unavailable'
    fi
}

probe() {
    local label="$1"
    shift

    if timeout --signal=TERM "$PROBE_TIMEOUT_SECONDS" "$@" >/dev/null 2>&1; then
        printf '%s=ok' "$label"
    else
        printf '%s=fail' "$label"
    fi
}

sample() {
    local memory pressure_cpu pressure_memory pressure_io gpu busy vram gtt xorg i3

    memory="$(awk '/MemAvailable|SwapFree|SwapTotal/ {sub(/:$/, "", $1); printf "%s=%s ", $1, $2}' /proc/meminfo)"
    pressure_cpu="$(read_value /proc/pressure/cpu)"
    pressure_memory="$(read_value /proc/pressure/memory)"
    pressure_io="$(read_value /proc/pressure/io)"
    gpu="/sys/class/drm/card1/device"
    busy="$(read_value "$gpu/gpu_busy_percent")"
    vram="$(read_value "$gpu/mem_info_vram_used")"
    gtt="$(read_value "$gpu/mem_info_gtt_used")"
    xorg="$(probe xorg xprop -root _NET_ACTIVE_WINDOW)"
    i3="$(probe i3 i3-msg -t get_workspaces)"

    log "sample $xorg $i3 gpu_busy_percent=$busy vram_used=$vram gtt_used=$gtt $memory psi_cpu=[$pressure_cpu] psi_memory=[$pressure_memory] psi_io=[$pressure_io]"
    [[ "$xorg" == 'xorg=ok' && "$i3" == 'i3=ok' ]]
}

snapshot() {
    local reason="$1"
    local snapshot_file="$STATE_DIR/snapshot-$(date +%Y%m%dT%H%M%S%z)-$reason.log"
    local gpu="/sys/class/drm/card1/device"

    {
        printf 'timestamp=%s reason=%s\n' "$(date --iso-8601=seconds)" "$reason"
        printf '\n[recent samples]\n'
        tail -n 120 "$LOG_FILE" 2>/dev/null || true
        printf '\n[pressure]\n'
        cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io 2>/dev/null || true
        printf '\n[memory]\n'
        awk '/MemTotal|MemAvailable|SwapTotal|SwapFree|Dirty|Writeback/ {print}' /proc/meminfo
        printf '\n[gpu]\n'
        for metric in gpu_busy_percent mem_info_vram_used mem_info_gtt_used reset_method; do
            printf '%s=' "$metric"
            cat "$gpu/$metric" 2>/dev/null || printf 'unavailable\n'
        done
        printf '\n[processes]\n'
        ps -eo pid,ppid,stat,ni,pcpu,pmem,rss,wchan:24,comm,args --sort=-pcpu | head -n 80
        printf '\n[x11 processes]\n'
        ps -eo pid,ppid,stat,pcpu,pmem,rss,wchan:24,comm,args | grep -E '(^ *PID|Xorg|gdm-x-session| i3$|brave|sioyek|kitty)' || true
        printf '\n[kernel tail]\n'
        journalctl -k -n 160 --no-pager 2>&1 || true
        printf '\n[system tail]\n'
        journalctl -n 160 --no-pager 2>&1 || true
    } >"$snapshot_file"

    log "snapshot reason=$reason file=$snapshot_file"
}

manual_snapshot=0
trap 'manual_snapshot=1' USR1

log "started interval_seconds=$INTERVAL_SECONDS probe_timeout_seconds=$PROBE_TIMEOUT_SECONDS"
failures=0
last_snapshot_epoch=0

while true; do
    if [[ ! -r "$XAUTHORITY" ]]; then
        failures=0
        log "sample x_session=not-ready"
        sleep "$INTERVAL_SECONDS"
        continue
    fi

    if ((manual_snapshot)); then
        snapshot manual
        manual_snapshot=0
    fi

    if sample; then
        failures=0
    else
        failures=$((failures + 1))
        log "probe_failure consecutive=$failures"
        now_epoch="$(date +%s)"
        if ((failures >= FAILURES_BEFORE_SNAPSHOT && now_epoch - last_snapshot_epoch >= 60)); then
            snapshot x11-probe-failure
            last_snapshot_epoch="$now_epoch"
        fi
    fi

    sleep "$INTERVAL_SECONDS"
done
