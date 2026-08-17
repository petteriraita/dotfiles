# Push-to-talk dictation for Fedora/i3/X11

A small command-driven dictation tool for holding a key, speaking, and pasting
local Whisper transcription into a terminal. It is designed for long prompts in
Codex CLI. It never presses Enter.

## Architecture

```text
key down -> `start` -> pw-record -> private WAV in $XDG_RUNTIME_DIR
                  `-> start/warm resident large-v3-turbo worker

key up   -> `stop` -> finalize WAV -> resident worker -> xclip -> xdotool paste
                                          |              |
                                          |              `-> no Enter
                                          `-> direct fallback if unavailable
```

- `pw-record` is the native PipeWire recorder. With no explicit target it follows
  PipeWire's current default source.
- faster-whisper runs `large-v3-turbo` through CTranslate2 on the CPU with INT8.
  A private Unix-socket worker keeps the model loaded between dictations and
  starts warming when recording begins. This machine's Radeon 860M is not
  exposed as a supported CTranslate2 GPU, so the eight physical Ryzen CPU cores
  remain the reliable backend.
- If the worker is stopped, stale, or crashes during a request, the controller
  recreates it automatically and retains the original direct-transcription path
  as a final fallback. Worker failure cannot create a second recorder.
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

This dotfiles repository also exposes `bin/ptt-dictation`, so from
`/home/pt/dev/dotfiles` the relative command works as written.

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
language = "en"               # skip automatic detection for English dictation
cpu_threads = 8

[worker]
enabled = true
startup_timeout_seconds = 20.0
request_timeout_seconds = 300.0
fallback_to_direct = true

[paste]
hotkey = "ctrl+shift+v"       # appropriate for kitty and most terminals
focus_original_window = true
```

For uncommitted machine-specific changes, create `config.local.toml`. It is
ignored by Git and is merged over the defaults. For example, restore automatic
language detection with:

```toml
[whisper]
language = ""
```

Set `PTT_CONFIG=/absolute/path/to/file.toml` to replace the project config
entirely.

The worker has no artificial RAM cap. On this machine it measured about 976 MiB
immediately after loading and about 1.1 GiB after transcription, comfortably
within the available memory. `large-v3-turbo` remains the tested default.

### What beam size means

Whisper generates text token by token. `beam_size = 5` keeps and compares up to
five promising token sequences while decoding instead of committing immediately
to the single highest-scoring next token. This can help with ambiguous speech,
names, and technical wording. A beam size of 1 is greedy decoding and may be
faster, but it can reduce accuracy. Beam size is not a model-size or RAM limit;
this project intentionally leaves it at 5.

## Commands

```bash
bin/ptt-dictation start
bin/ptt-dictation stop
bin/ptt-dictation cancel
bin/ptt-dictation status
bin/ptt-dictation toggle
bin/ptt-dictation doctor
bin/ptt-dictation worker-start
bin/ptt-dictation worker-status
bin/ptt-dictation worker-stop
```

- `start` begins recording in the background, remembers the focused X11
  window, and returns to the shell immediately. Returning to the prompt does
  not mean recording stopped; use `status` to confirm it is active.
- `stop` stops, transcribes, copies, and pastes without Enter.
- `stop --no-paste` prints the transcription instead.
- `cancel` discards an active recording without running Whisper.
- `toggle` supports a press-once/press-again binding, but press/release bindings
  provide the desired push-to-talk behavior.
- `worker-start` loads Turbo and waits until it is ready. Normal Page Down usage
  starts it automatically, so this command is mainly diagnostic.
- `worker-status` shows the phase, PID, and current resident memory.
- `worker-stop` releases the resident model memory. The next recording starts it
  again automatically.

## Exact i3 binding

Kanata taps virtual F13 when physical Page Down is pressed and virtual F14 when
it is released. On this X11 keyboard map those appear as raw keycodes 191 and
192 without keysyms, so these bindings are installed in
`/home/pt/dev/dotfiles/i3config`:

```i3config
set $ptt /home/pt/dev/dotfiles/push-to-talk/bin/ptt-dictation
bindcode 191 exec --no-startup-id $ptt start
bindcode 192 exec --no-startup-id $ptt stop
```

Then reload i3:

```bash
i3-msg reload
```

### Kanata

Kanata is currently a root system service on this machine. Do not run the
dictation command directly from Kanata: it would inherit the wrong user,
`DISPLAY`, clipboard, cache, and state directories.

The physical `pgdn` key is included in `defsrc` and runs the `@ptt` action on
every layer. `@ptt` taps F13 on physical press and F14 on physical release. The
user-session i3 bindings above run the two commands with the correct X11
environment. The separate `pgdn` action already present on the navigation layer
is unchanged, so that layer combination still produces normal Page Down.

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

Focus Codex CLI, hold the physical Page Down key, dictate, and release it.
The result should appear at the prompt without being submitted.

The automated development test verified duplicate `start`, live `status`, real
default-microphone recording, `large-v3-turbo` transcription, cleanup, and the
return to `idle`. A separate disposable kitty/tmux test verified actual X11
clipboard insertion without Enter and restored both focus and clipboard.

The resident-worker tests additionally verified cold startup, two requests on
the same PID, clean shutdown, automatic recreation after an unexpected exit,
and direct fallback after a simulated worker failure.

## Diagnostics

Run the built-in check first:

```bash
bin/ptt-dictation doctor
bin/ptt-dictation status
bin/ptt-dictation worker-status
```

Watch controller and component logs:

```bash
tail -f ~/.local/state/ptt-dictation/ptt.log
tail -f ~/.local/state/ptt-dictation/recorder.log
tail -f ~/.local/state/ptt-dictation/clipboard.log
tail -f ~/.local/state/ptt-dictation/worker.log
```

The log files are all under `~/.local/state/ptt-dictation/`:

- `ptt.log` is the main log. It records start/stop, Whisper results, paste
  delivery, warnings, and Python tracebacks. Usually, this is the first file to
  inspect.
- `recorder.log` contains errors written by `pw-record` and PipeWire.
- `clipboard.log` contains errors written by `xclip`.
- `worker.log` captures uncaught startup failures from the resident Whisper
  process. Normal worker lifecycle and request timings are recorded in
  `ptt.log`.

An empty `recorder.log` or `clipboard.log` is normal when that component has not
reported an error.

To inspect recent failures without following the files continuously:

```bash
tail -n 100 ~/.local/state/ptt-dictation/ptt.log
grep -E ' (ERROR|WARNING) ' ~/.local/state/ptt-dictation/ptt.log | tail -n 30
journalctl -u kanata.service -n 100 --no-pager
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
bin/ptt-dictation worker-status
tail -n 100 ~/.local/state/ptt-dictation/ptt.log
tail -n 100 ~/.local/state/ptt-dictation/worker.log
```

- A first-run network failure affects only the model download; retry the command.
- An empty transcription usually means the recording was silent or too short.
- English is forced by default to avoid language-detection latency. Set
  `language = ""` in `config.local.toml` only when multilingual detection is
  needed. Reducing `beam_size` or selecting a smaller model may be faster but
  can reduce transcription quality.
- To force a clean model download, remove only `~/.cache/ptt-dictation/` and run
  the known-sample test again.
- If the worker appears stale, run `bin/ptt-dictation worker-stop`; the next
  recording recreates it. Direct fallback remains available if startup fails.

### Clipboard/paste failures

```bash
tail -n 100 ~/.local/state/ptt-dictation/ptt.log
tail -n 100 ~/.local/state/ptt-dictation/clipboard.log
printf 'clipboard test' | xclip -selection clipboard
xclip -selection clipboard -out
xdotool getactivewindow getwindowname
```

Verify `DISPLAY=:0` exists in the environment that launches the command. If text
is copied but not pasted, adjust `[paste].hotkey`; GUI editors generally use
`ctrl+v`, while kitty uses `ctrl+shift+v`. The transcription remains available
in the clipboard if simulated paste or restoration of the original window
fails. Paste it manually with `Ctrl+Shift+V` in a terminal or `Ctrl+V` in most
GUI applications. A stale or unresponsive original window is treated as a
clipboard-only success rather than losing the completed transcription.

## Uninstall and cleanup

No new system service or Fedora package was installed. The existing Kanata and
i3 configurations were updated. To remove the project completely:

1. Run `bin/ptt-dictation cancel` if recording, then
   `bin/ptt-dictation worker-stop`.
2. Remove the three i3 lines shown above and run `i3-msg reload`.
3. Remove any Kanata `f13` mapping you added.
4. Remove generated data and the project:

```bash
cd /home/pt/dev/dotfiles
unlink ~/.local/bin/ptt-dictation
unlink ~/bin/ptt-dictation
unlink /home/pt/dev/dotfiles/bin/ptt-dictation
rm -rf push-to-talk/.venv
rm -rf ~/.cache/ptt-dictation ~/.local/state/ptt-dictation
rm -rf /run/user/$(id -u)/ptt-dictation
git rm -r push-to-talk
```

If the project has not been committed, replace the final `git rm` with
`rm -rf push-to-talk`. Review those paths before running the cleanup commands.
