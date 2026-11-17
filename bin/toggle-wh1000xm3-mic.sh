#!/usr/bin/env bash

# Toggle the paired WH-1000XM3 headset. On connection, select high-quality
# stereo playback and keep microphone input on the laptop.
set -u

device='CC:98:8B:49:F0:8F'
name='WH-1000XM3'
card='bluez_card.CC_98_8B_49_F0_8F'

# Ignore repeated presses while a connection is still being established.
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/toggle-wh1000xm3-${UID}.lock"
flock -n 9 || exit 0

notify() {
    notify-send --app-name=Bluetooth "$name" "$1"
}

connected() {
    bluetoothctl info "$device" | grep -q 'Connected: yes'
}

audio_ready() {
    pactl list short sinks | awk '{print $2}' | grep -Eq '^bluez_output\.CC[:_]98[:_]8B[:_]49[:_]F0[:_]8F\.'
}

wait_for_audio() {
    for _ in {1..15}; do
        audio_ready && return 0
        sleep 1
    done
    return 1
}

# A Bluetooth link can remain connected even when its audio connection failed.
if connected && audio_ready; then
    notify 'Disconnecting…'
    if bluetoothctl disconnect "$device"; then
        notify 'Disconnected'
    else
        notify 'Could not disconnect'
    fi
    exit 0
fi

notify 'Connecting…'
for attempt in 1 2; do
    # Clear a stale Bluetooth link before retrying the audio connection.
    if connected; then
        bluetoothctl disconnect "$device" >/dev/null || true
        sleep 2
    fi

    if timeout 25s bluetoothctl connect "$device" && wait_for_audio; then
        break
    fi

    if (( attempt == 2 )); then
        notify 'Could not connect audio — check that the headset is on and nearby'
        exit 1
    fi
    notify 'Audio did not connect — retrying…'
done

# The audio sink is present now; PipeWire may still be registering its card.
for _ in {1..5}; do
    pactl list short cards | awk '{print $2}' | grep -Fxq "$card" && break
    sleep 1
done
if ! pactl list short cards | awk '{print $2}' | grep -Fxq "$card"; then
    notify 'Connected, but the audio card did not appear'
    exit 1
fi

# Hands-free mode reduces playback to mono 16 kHz. Use stereo A2DP by default;
# the headset microphone remains available by manually choosing HFP for calls.
if ! pactl set-card-profile "$card" a2dp-sink; then
    notify 'Connected, but stereo playback could not be selected'
    exit 1
fi

for _ in {1..10}; do
    sink_name="$(pactl list short sinks | awk '$2 ~ /^bluez_output\.CC[:_]98[:_]8B[:_]49[:_]F0[:_]8F/ { print $2; exit }')"
    if [[ -n "$sink_name" ]]; then
        pactl set-default-sink "$sink_name" || exit 1
        # Only select a real laptop microphone, never an output monitor.
        source_name="$(pactl list short sources | awk '$2 ~ /^alsa_input\./ && $2 ~ /Mic1/ { print $2; exit }')"
        if [[ -n "$source_name" ]]; then
            pactl set-default-source "$source_name" || exit 1
        fi
        notify 'Connected — stereo playback selected'
        exit 0
    fi
    sleep 1
done

notify 'Connected — stereo output did not appear'
exit 1
