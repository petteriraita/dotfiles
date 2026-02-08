#!/usr/bin/env bash

about_to_suspend=1
while true; do
	## get the capacities
	capacity=$(cat /sys/class/power_supply/BAT0/capacity)
	status=$(cat /sys/class/power_supply/BAT0/status)

	### the basic reset if everything is okay or charging started
	if [[ "$capacity" -ge 30 || "$status" == "Charging" ]]; then
		about_to_suspend=1
	fi

	if [[ "$status" == "Discharging" && "$capacity" -le 25 ]]; then
		notify-send "Low Battery" "Battery at ${capacity}%"
	fi

	if [[ "$status" == "Not charging" && "$capacity" -le 25 ]]; then
		notify-send -u critical "CRITICAL BATTERY" "Plug in charger!"
	fi

	if [[ ("$status" == "Discharging" || "$status" == "Not charging") && "$capacity" -le 15 ]]; then
		### so if the about_to_suspend was set already to 0 the last time, then we just suspend
		if [[ "$about_to_suspend" -eq 0 ]]; then
			about_to_suspend=1
			systemctl suspend
		fi
		### if its the first, time, giving the user 120 seconds
		notify-send -u critical "suspending in 120seconds"
		about_to_suspend=0
	fi
	sleep 120
done
