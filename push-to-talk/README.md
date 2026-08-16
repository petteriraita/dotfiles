# Push-to-talk dictation for Fedora/i3/X11

A small command-driven dictation tool for holding a key, speaking, and pasting
local Whisper transcription into a terminal. It is designed for long prompts in
Codex CLI. It never presses Enter.

## Architecture

```text
key down -> `start` -> pw-record -> private WAV in $XDG_RUNTIME_DIR
key up   -> `stop`  -> finalize WAV -> faster-whisper -> xclip -> xdotool paste
                                               |
                                               `-> WAV deleted in finally
```

- `pw-record` is the native PipeWire recorder. With no explicit target it follows
  PipeWire's current default source.
- faster-whisper runs `large-v3-turbo` through CTranslate2 on the CPU with INT8.
  This machine's Radeon 860M is not supported by CTranslate2's prebuilt GPU path;
  the Ryzen CPU has AVX-512 and is the simplest supported option.
- `xclip` owns the X11 clipboard and `xdotool` sends one `Ctrl+Shift+V`. This is
  much more reliable in terminals than simulating every character.
- The X11 window focused when recording starts is remembered and refocused before
  paste. Notifications do not redirect the output.
- A locked state file prevents duplicate recorders and duplicate `stop` actions.
  A new recording is refused while the previous recording is transcribing.
- Audio exists only under `$XDG_RUNTIME_DIR/ptt-dictation/` and is removed after
  success, failure, or cancellation.
- Logs live in `~/.local/state/ptt-dictation/`. Models live in the normal cache at
  `~/.cache/ptt-dictation/`.

## Dependencies

Runtime Fedora packages:

- `pipewire-utils` (`pw-record`)
- `xclip`
- `xdotool`
- `libnotify` (`notify-send`)

All four are already installed on this Fedora 43 machine. `ffmpeg`, `arecord`,
and `parec` were inspected but are not needed. No sudo installation was performed.

Python dependencies are locked in `uv.lock`; the direct dependency is:

- `faster-whisper>=1.2.1,<2`

The project uses the already-installed `uv` and Python 3.13. Fedora's system
Python 3.14 is deliberately not modified.

Optional test-only commands are `espeak-ng`, `tmux`, and `kitty`; they are not
needed for normal dictation.

## Setup

```bash
cd /home/pt/dev/dotfiles/push-to-talk
uv sync --frozen --python 3.13
bin/ptt-dictation doctor
```

For use from any directory, create a user-local launcher symlink:

```bash
ln -s /home/pt/dev/dotfiles/push-to-talk/bin/ptt-dictation ~/.local/bin/ptt-dictation
ptt-dictation doctor
```

The first transcription downloads about 1.6 GB of model data to
`~/.cache/ptt-dictation/`. Later runs reuse it. The launcher disables Hugging
Face's optional Xet transfer path because it stalled on this host; ordinary HTTP
completed successfully.

## Configuration

Defaults are in `config.toml`. The main settings are:

```toml
[whisper]
model = "large-v3-turbo"
device = "cpu"
compute_type = "int8"
language = ""                 # automatic detection; use "en" to force English
cpu_threads = 8

[paste]
hotkey = "ctrl+shift+v"       # appropriate for kitty and most terminals
focus_original_window = true
```

For uncommitted machine-specific changes, create `config.local.toml`. It is
ignored by Git and is merged over the defaults. For example:

```toml
[whisper]
language = "en"
```

Set `PTT_CONFIG=/absolute/path/to/file.toml` to replace the project config
entirely.

If CPU transcription proves too slow, try `model = "small.en"` for English or
`model = "medium"` for multilingual speech. The requested `large-v3-turbo` is
the tested default and fits this machine's 24 GB RAM.

## Commands

```bash
bin/ptt-dictation start
bin/ptt-dictation stop
bin/ptt-dictation cancel
bin/ptt-dictation status
bin/ptt-dictation toggle
bin/ptt-dictation doctor
```

- `start` begins recording and remembers the focused X11 window.
- `stop` stops, transcribes, copies, and pastes without Enter.
- `stop --no-paste` prints the transcription instead.
- `cancel` discards an active recording without running Whisper.
- `toggle` supports a press-once/press-again binding, but press/release bindings
  provide the desired push-to-talk behavior.

## Exact i3 binding

The recommended virtual key is `F13`, especially if Kanata will produce the
key. Add these exact lines to the user i3 configuration:

```i3config
set $ptt /home/pt/dev/dotfiles/push-to-talk/bin/ptt-dictation
bindsym --no-repeat F13 exec --no-startup-id $ptt start
bindsym --release --no-repeat F13 exec --no-startup-id $ptt stop
```

Then reload i3:

```bash
i3-msg reload
```

For a physical key handled directly by i3, replace both occurrences of `F13`
with its i3 name, such as `Pause`.

### Kanata

Kanata is currently a root system service on this machine. Do not run the
dictation command directly from Kanata: it would inherit the wrong user,
`DISPLAY`, clipboard, cache, and state directories.

Instead, map the desired physical key or Kanata layer position to `f13`. Kanata
will emit normal F13 key-down and key-up events, and the user-session i3 bindings
above will run the two commands with the correct X11 environment. The exact
Kanata layer cell depends on which physical key you choose; replace that cell's
action with `f13` in `/home/pt/dev/dotfiles/kanata/config.kbd`.

## Tests

### 1. Default microphone

This records for two seconds, validates the WAV, prints its duration/size, and
deletes it:

```bash
cd /home/pt/dev/dotfiles/push-to-talk
bin/ptt-dictation record-test --seconds 2
```

To listen to the result, keep it explicitly:

```bash
bin/ptt-dictation record-test --seconds 3 --keep /tmp/ptt-mic-test.wav
ffplay -nodisp -autoexit /tmp/ptt-mic-test.wav
unlink /tmp/ptt-mic-test.wav
```

### 2. Whisper with a known sample

```bash
espeak-ng -s 145 -w /tmp/ptt-known.wav \
  'The quick brown fox jumps over the lazy dog. Push to talk dictation is ready for Codex.'
bin/ptt-dictation transcribe-file /tmp/ptt-known.wav
unlink /tmp/ptt-known.wav
```

The implemented configuration produced:

```text
The quick brown fox jumps over the lazy dog. Push to talk dictation is ready for codex.
```

Add `--paste` to `transcribe-file` only when a safe target window is focused.

### 3. Clipboard insertion

Run this in a scratch terminal. When it exits, the text should be visible at the
shell prompt but must not execute:

```bash
bin/ptt-dictation paste-test 'PTT clipboard insertion passed'
```

Use `--clipboard-only` to test copying without synthesizing the paste shortcut.

### 4. Complete push-to-talk cycle

Before adding the hotkey, test the same two commands manually:

```bash
bin/ptt-dictation start
# Speak a sentence, then:
bin/ptt-dictation stop --no-paste
```

Then add/reload the i3 binding, focus Codex CLI, hold F13, dictate, and release.
The result should appear at the prompt without being submitted.

The automated development test verified duplicate `start`, live `status`, real
default-microphone recording, `large-v3-turbo` transcription, cleanup, and the
return to `idle`. A separate disposable kitty/tmux test verified actual X11
clipboard insertion without Enter and restored both focus and clipboard.

## Diagnostics

Run the built-in check first:

```bash
bin/ptt-dictation doctor
bin/ptt-dictation status
```

Watch controller and component logs:

```bash
tail -f ~/.local/state/ptt-dictation/ptt.log
tail -f ~/.local/state/ptt-dictation/recorder.log
tail -f ~/.local/state/ptt-dictation/clipboard.log
```

### Microphone failures

```bash
pactl info | grep 'Default Source'
wpctl status
wpctl get-volume @DEFAULT_AUDIO_SOURCE@
bin/ptt-dictation record-test --seconds 3 --keep /tmp/ptt-mic-test.wav
```

If the WAV is silent, select/unmute the intended source with `wpctl` or the
desktop audio controls, then repeat `record-test`. `recorder.log` contains
PipeWire connection errors.

### Transcription failures or slowness

```bash
du -sh ~/.cache/ptt-dictation
bin/ptt-dictation doctor
tail -n 100 ~/.local/state/ptt-dictation/ptt.log
```

- A first-run network failure affects only the model download; retry the command.
- An empty transcription usually means the recording was silent or too short.
- For lower latency, set `language = "en"`, reduce `beam_size`, or select a
  smaller model in `config.local.toml`.
- To force a clean model download, remove only `~/.cache/ptt-dictation/` and run
  the known-sample test again.

### Clipboard/paste failures

```bash
printf 'clipboard test' | xclip -selection clipboard
xclip -selection clipboard -out
xdotool getactivewindow getwindowname
```

Verify `DISPLAY=:0` exists in the environment that launches the command. If text
is copied but not pasted, adjust `[paste].hotkey`; GUI editors generally use
`ctrl+v`, while kitty uses `ctrl+shift+v`. The transcription remains available
in the clipboard if simulated paste fails.

## Uninstall and cleanup

No system service, Fedora package, i3 line, or Kanata line was installed by this
project. To remove it completely:

1. Run `bin/ptt-dictation cancel` if recording.
2. Remove the three i3 lines shown above and run `i3-msg reload`.
3. Remove any Kanata `f13` mapping you added.
4. Remove generated data and the project:

```bash
cd /home/pt/dev/dotfiles
unlink ~/.local/bin/ptt-dictation
rm -rf push-to-talk/.venv
rm -rf ~/.cache/ptt-dictation ~/.local/state/ptt-dictation
rm -rf /run/user/$(id -u)/ptt-dictation
git rm -r push-to-talk
```

If the project has not been committed, replace the final `git rm` with
`rm -rf push-to-talk`. Review those paths before running the cleanup commands.
