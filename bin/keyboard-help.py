#!/usr/bin/python3
"""Mouse-triggered keyboard/laptop freeze diagnostics; save evidence before diagnosis."""
import concurrent.futures
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading

STATE = Path.home() / '.local/state/keyboard-help'
NOTE = Path('/home/pt/dev/personal/knowledge/obsidian_vault/problem of linux thinkpad freezing bug freeze linux fail.md')


def run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=8)
        return f'$ {args!r}\nexit={result.returncode}\n{result.stdout}{result.stderr}'
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f'$ {args!r}\n{exc}\n'


def diagnose(snapshot_only=False):
    os.umask(0o077)
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'launcher.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        folder = STATE / datetime.datetime.now().astimezone().strftime('%Y-%m-%dT%H-%M-%S.%f%z')
        folder.mkdir()
        # Capture focus and current key state before a terminal changes focus/layer.
        focus = run(['xprop', '-root', '_NET_ACTIVE_WINDOW'])
        (folder / 'focus.txt').write_text(focus)
        match = re.search(r'window id # (0x[0-9a-fA-F]+)', focus)
        if match and match[1] != '0x0':
            (folder / 'window.txt').write_text(run(['xprop', '-id', match[1], 'WM_CLASS', '_NET_WM_PID']))
        commands = {
            'devices': ['xinput', '--list', '--long'],
            'modifier-map': ['xmodmap', '-pm'],
            'xset': ['xset', 'q'],
            'input-devices': ['cat', '/proc/bus/input/devices'],
            'kanata': ['journalctl', '-b', '-u', 'kanata.service', '--since', '-15min', '-n', '2500', '--no-pager'],
            'watcher': ['journalctl', '--user', '-b', '-u', 'kanata-layer-watch.service', '--since', '-15min', '-n', '1000', '--no-pager'],
            'kernel': ['journalctl', '-b', '-k', '--since', '-15min', '-n', '1000', '--no-pager'],
            'previous-kernel': ['journalctl', '-b', '-1', '-k', '-n', '1500', '--no-pager'],
            'previous-warnings': ['journalctl', '-b', '-1', '-p', 'warning', '-n', '1000', '--no-pager'],
            'system': ['journalctl', '-b', '--since', '-15min', '-n', '1500', '--no-pager'],
            'session': ['journalctl', '--user', '-b', '--since', '-15min', '-n', '1000', '--no-pager'],
            'boots': ['journalctl', '--list-boots', '-n', '5', '--no-pager'],
            'system-info': ['uname', '-a'],
            'memory': ['cat', '/proc/meminfo', '/proc/pressure/cpu', '/proc/pressure/memory', '/proc/pressure/io'],
            'i3': ['i3-msg', '-t', 'get_workspaces'],
            'service': ['systemctl', 'show', 'kanata.service', '-p', 'MainPID', '-p', 'ActiveState', '-p', 'SubState', '-p', 'NRestarts'],
            'processes': ['ps', '-eLo', 'pid,tid,stat,wchan:32,comm'],
            'freeze-monitor': ['tail', '-n', '100', str(Path.home() / '.local/state/freeze-monitor/samples.log')],
        }
        monitor = Path.home() / '.local/state/freeze-monitor'
        # Preserve bounded copies: the monitor's files may rotate after this click.
        commands['freeze-monitor-previous'] = ['tail', '-n', '100', str(monitor / 'samples.log.1')]
        for index, snapshot in enumerate(sorted(monitor.glob('snapshot-*.log'))[-3:], 1):
            commands[f'freeze-snapshot-{index}'] = ['tail', '-n', '1000', str(snapshot)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as pool:
            futures = {name: pool.submit(run, args) for name, args in commands.items()}
            for name, future in futures.items():
                (folder / f'{name}.txt').write_text(future.result())
        # Snapshot each keyboard's pressed-key state, never a stream of typed keys.
        listing = (folder / 'devices.txt').read_text()
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            states = {}
            for line in listing.splitlines():
                if 'slave  keyboard' in line.lower() or 'slave keyboard' in line.lower():
                    device = re.search(r'id=(\d+)', line)
                    if device:
                        states[device[1]] = pool.submit(run, ['xinput', '--query-state', device[1]])
            for device, future in states.items():
                (folder / f'device-{device}.txt').write_text(future.result())
        prompt = (f'I clicked Freeze help because either my keyboard input is broken or my laptop/desktop '
                  f'is freezing, severely lagging, or has just recovered/rebooted after a freeze. '
                  f'Determine which is happening now from the evidence; do not assume a keyboard-only issue. '
                  f'Investigate using the pre-launch logs already saved in {folder}. Read the history in {NOTE}. '
                  'If I can respond, ask briefly whether this is keyboard-only or a wider laptop freeze, '
                  'and when it happened, but do not wait for a typed reply before investigating. '
                  'Distinguish current-boot evidence from previous-boot and older freeze-monitor snapshots. '
                  'For a wider freeze, examine kernel/AMDGPU errors, Xorg/i3 responsiveness, memory/PSI, '
                  'suspend/resume and display hotplug activity, and the existing freeze-monitor logs. '
                  'This is read-only diagnosis: do not restart Kanata, change layers, inject keys, kill apps, '
                  'change GPU/system settings, or reboot. For keyboard issues compare physical input, '
                  'Kanata/uinput, X11 key/modifier state, input grabs, '
                  'and app/terminal-specific issues. No continuous keylogging. Do not assume TCP BrokenPipe '
                  'warnings prove a crash. I may be unable to type replies; proceed with safe read-only '
                  'checks. Explain which kind of failure the evidence supports, whether a fix is established '
                  'or still unknown, and the smallest justified recovery/fix with exact steps. '
                  'Always tell me where the logs were saved. A fully frozen machine may prevent this launcher '
                  'from running; after reboot use the previous-boot logs and preserved monitor evidence.')
        (folder / 'prompt.txt').write_text(prompt + '\n')
        print(folder, flush=True)
        if not snapshot_only:
            codex = str(Path.home() / '.npm-global/bin/codex')
            # Keep the lock until this diagnostic window closes to prevent double-click duplicates.
            with (folder / 'launcher.log').open('w') as log:
                subprocess.run(['kitty', '--title', 'Keyboard / laptop freeze diagnosis', '--hold',
                                codex, '--no-daemon', '-C', str(Path.home()),
                                '-s', 'read-only', '-a', 'never', prompt], stdout=log, stderr=log)


def bar():
    child = subprocess.Popen(['i3status', '--config', str(Path.home() / '.config/i3status/config')],
                             stdout=subprocess.PIPE, text=True)
    def stop(*_):
        child.terminate()
        raise SystemExit
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def clicks():
        for line in sys.stdin:
            try:
                event = json.loads(line.strip().lstrip(','))
                if event.get('name') == 'keyboard-help' and event.get('button') == 1:
                    launcher = subprocess.Popen([sys.executable, __file__], stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     start_new_session=True)
                    threading.Thread(target=launcher.wait, daemon=True).start()
            except (ValueError, AttributeError):
                continue
    threading.Thread(target=clicks, daemon=True).start()

    def bluetooth_is_default_output():
        try:
            result = subprocess.run(['pactl', 'get-default-sink'], capture_output=True,
                                    text=True, timeout=2, check=True)
            return result.stdout.strip().startswith('bluez_output.')
        except (OSError, subprocess.SubprocessError):
            return False

    try:
        header = json.loads(child.stdout.readline())
        header['click_events'] = True
        print(json.dumps(header), flush=True)
        print(child.stdout.readline().strip(), flush=True)
        for line in child.stdout:
            comma = ',' if line.lstrip().startswith(',') else ''
            blocks = json.loads(line.strip().lstrip(','))
            if bluetooth_is_default_output():
                for block in blocks:
                    if block.get('name') == 'volume':
                        block['full_text'] += ' B'
                        break
            blocks.insert(0, {'name': 'keyboard-help', 'full_text': 'Freeze help', 'color': '#ffcc66'})
            print(comma + json.dumps(blocks), flush=True)
    finally:
        child.terminate()
        child.wait()


if __name__ == '__main__':
    if '--bar' in sys.argv:
        bar()
    else:
        diagnose('--snapshot-only' in sys.argv)
