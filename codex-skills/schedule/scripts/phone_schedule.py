#!/usr/bin/env python3
"""Request native Android actions; an intent is not proof of persistence."""
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import shlex
import subprocess
import sys
from zoneinfo import ZoneInfo

SSH = ['ssh', '-F', str(Path.home() / '.ssh/config'), '-o', 'BatchMode=yes',
       '-o', 'ConnectTimeout=10', 'android-phone']


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def check():
    try:
        r = subprocess.run(SSH + ['date +%s; getprop persist.sys.timezone; command -v am'],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        fail('Phone SSH unavailable/timed out. Tell the user immediately. Stop phone actions; check Tailscale status and the configured phone peer, then Termux sshd/key. Do not loop or install alternative access tools.')
    if r.returncode:
        fail('Phone SSH failed. Tell the user immediately; follow android-phone-ssh for a targeted Tailscale/SSH diagnostic.\n' + r.stderr.strip())
    lines = r.stdout.strip().splitlines()
    try:
        now = datetime.fromtimestamp(int(lines[0]), ZoneInfo(lines[1]))
        launcher = lines[2]
    except (ValueError, IndexError, KeyError):
        fail('Connected, but phone time/timezone or native am launcher could not be read.')
    return now, launcher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('check')
    alarm = sub.add_parser('alarm')
    alarm.add_argument('--at', required=True, help='ISO date/time with UTC offset; next occurrence only')
    alarm.add_argument('--label', required=True)
    contact = sub.add_parser('contact')
    contact.add_argument('--name', required=True)
    contact.add_argument('--number', required=True)
    contact.add_argument('--notes', default='')
    args = parser.parse_args()
    if args.action == 'contact':
        fail('Contact editor automation is disabled by user preference. Use an authorized Google People API or Android Contacts Provider CLI, then read back the account/name/number. No contact editor was opened.')
    if args.action == 'alarm':
        try:
            target = datetime.fromisoformat(args.at)
        except ValueError:
            parser.error('--at needs ISO date/time with UTC offset')
        if target.tzinfo is None or target.second or target.microsecond:
            parser.error('--at needs a UTC offset and whole minutes')
        if not args.label.strip() or len(args.label) > 200:
            parser.error('--label must have 1–200 characters')
    if args.action == 'contact':
        digits = args.number.removeprefix('+')
        if not args.name.strip() or not args.number.startswith('+') or not digits.isdigit() or not 7 <= len(digits) <= 15:
            parser.error('provide a searchable name and +country-code phone number')
    now, launcher = check()
    if args.action == 'check':
        print(json.dumps({'status': 'connected', 'phone_time': now.isoformat(), 'timezone': str(now.tzinfo)}))
        return
    if args.action == 'alarm':
        local = target.astimezone(now.tzinfo)
        next_time = now.replace(hour=local.hour, minute=local.minute, second=0, microsecond=0)
        if next_time <= now:
            next_time += timedelta(days=1)
        if target <= now or local != next_time:
            fail('Requested date is not the next occurrence of that phone-local time. Native alarm intent cannot represent it safely.')
        intent = [launcher, 'start', '--user', '0', '-a', 'android.intent.action.SET_ALARM',
                  '-p', 'com.google.android.deskclock', '--ei', 'android.intent.extra.alarm.HOUR', str(local.hour),
                  '--ei', 'android.intent.extra.alarm.MINUTES', str(local.minute),
                  '--es', 'android.intent.extra.alarm.MESSAGE', args.label,
                  '--es', 'android.intent.extra.alarm.RINGTONE', 'silent',
                  '--ez', 'android.intent.extra.alarm.VIBRATE', 'true',
                  '--ez', 'android.intent.extra.alarm.SKIP_UI', 'true']
    else:
        intent = [launcher, 'start', '--user', '0', '-a', 'android.intent.action.INSERT',
                  '-t', 'vnd.android.cursor.dir/contact', '-p', 'com.google.android.contacts',
                  '--es', 'name', args.name, '--es', 'phone', args.number, '--es', 'notes', args.notes]
    try:
        r = subprocess.run(SSH + [shlex.join(intent)], capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        fail('Native request timed out: outcome UNKNOWN. Inspect the phone before retrying to avoid duplicates.')
    output = r.stdout + r.stderr
    if r.returncode or any(s in output for s in ('Permission Denial', 'SecurityException', 'Error:', 'Exception')):
        fail('Native request failed/rejected; inspect before retrying.\n' + output.strip())
    print(json.dumps({'status': 'requested_unverified', 'action': args.action,
                      'next_step': 'Check date/time/enabled/label, Silent sound, vibration on, no repeats in Google Clock.'
                      if args.action == 'alarm' else 'Select intended Google account, never SIM/device, tap Save, and verify contact/account.'}))


if __name__ == '__main__':
    main()
