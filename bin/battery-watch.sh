#!/usr/bin/env bash

notify-send "test"
capacity=$(cat /sys/class/power_supply/BAT0/capacity)
status=$(cat /sys/class/power_supply/BAT0/status)

echo "${capacity}"
echo "${status}"

while true; do
	if [[ "$status" == "Discharging" && "$capacity" -le 25 ]]; then
		notify-send "Low Battery" "Battery at ${capacity}%"
	fi

	if [[ "$status" == "Not charging" && "$capacity" -le 25 ]]; then
		notify-send -u critical "CRITICAL BATTERY" "Plug in charger!"
	fi

	if [[ "$status" == "Discharging" || "$status" == "Not charging" && "$capacity" -le 15 ]]; then
		systemctl suspend
	fi
	sleep 60
done
