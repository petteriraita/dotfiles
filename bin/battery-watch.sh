#!/usr/bin/env bash
set -euo pipefail

BATTERY_PATH="/sys/class/power_supply/BAT0"
CHECK_INTERVAL_SECONDS=60
LOW_THRESHOLD=25
CRITICAL_THRESHOLD=15
RESET_THRESHOLD=30
SUSPEND_DELAY_MINUTES=4
SUSPEND_DELAY_SECONDS=$((SUSPEND_DELAY_MINUTES * 60))
SUSPEND_COOLDOWN_SECONDS=900
SUSPEND_STAMP_FILE="/tmp/battery-watch.last-suspend-at"

last_notified_level=""
pending_notification_ids=()
suspend_at=0

log() {
    logger -t battery-watch "$1"
}

read_battery_field() {
    local field="$1"
    cat "$BATTERY_PATH/$field"
}

reset_state() {
    last_notified_level=""
    suspend_at=0
}

clear_pending_notifications() {
    local notification_id

    for notification_id in "${pending_notification_ids[@]}"; do
        dunstctl close "$notification_id" || true
    done
    pending_notification_ids=()
}

notify_once() {
    local level="$1"
    local urgency="$2"
    local title="$3"
    local body="$4"

    if [[ "$last_notified_level" == "$level" ]]; then
        return
    fi

    local notification_id
    notification_id="$(notify-send -p -u "$urgency" "$title" "$body")"
    pending_notification_ids+=("$notification_id")
    last_notified_level="$level"
    log "$title - $body"
}

suspend_recently_attempted() {
    if [[ ! -f "$SUSPEND_STAMP_FILE" ]]; then
        return 1
    fi

    local last_attempt
    last_attempt="$(cat "$SUSPEND_STAMP_FILE" 2>/dev/null || echo 0)"
    (($(date +%s) - last_attempt < SUSPEND_COOLDOWN_SECONDS))
}

attempt_suspend() {
    if suspend_recently_attempted; then
        log "Skipping suspend attempt because cooldown is still active"
        return
    fi

    date +%s >"$SUSPEND_STAMP_FILE"
    log "Attempting suspend at critical battery"
    pending_notification_ids+=("$(notify-send -p -u critical "Suspending now" "Battery stayed at or below ${CRITICAL_THRESHOLD}% for ${SUSPEND_DELAY_MINUTES} minutes")")
    loginctl lock-session || true
    sleep 2

    if ! timeout --foreground 20s systemctl suspend; then
        log "Suspend command failed or timed out"
        pending_notification_ids+=("$(notify-send -p -u critical "Suspend failed" "Auto-suspend did not complete; check journalctl -t battery-watch")")
    fi
}

if [[ ! -r "$BATTERY_PATH/capacity" || ! -r "$BATTERY_PATH/status" ]]; then
    log "Battery path $BATTERY_PATH is not readable"
    exit 1
fi

while true; do
    capacity="$(read_battery_field capacity)"
    status="$(read_battery_field status)"

    if [[ "$capacity" -ge "$RESET_THRESHOLD" || "$status" == "Charging" ]]; then
        clear_pending_notifications
        reset_state
    fi

    if [[ "$status" == "Discharging" && "$capacity" -le "$LOW_THRESHOLD" ]]; then
        notify_once "low" "normal" "Low Battery" "Battery at ${capacity}%"
    fi

    if [[ "$status" == "Not charging" && "$capacity" -le "$LOW_THRESHOLD" ]]; then
        notify_once "not-charging" "critical" "Battery not charging" "Battery at ${capacity}%; plug in charger"
    fi

    if [[ ("$status" == "Discharging" || "$status" == "Not charging") && "$capacity" -le "$CRITICAL_THRESHOLD" ]]; then
        if [[ "$suspend_at" -gt 0 && "$(date +%s)" -ge "$suspend_at" ]]; then
            suspend_at=0
            attempt_suspend
        elif [[ "$suspend_at" -eq 0 ]]; then
            suspend_at="$(( $(date +%s) + SUSPEND_DELAY_SECONDS ))"
            notify_once "critical" "critical" "Suspending soon" "Battery still at or below ${CRITICAL_THRESHOLD}%; suspending in ${SUSPEND_DELAY_MINUTES} minutes"
        fi
    fi

    sleep "$CHECK_INTERVAL_SECONDS"
done
