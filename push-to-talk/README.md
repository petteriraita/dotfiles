# Push-to-talk dictation for Fedora/i3/X11

A small command-driven dictation tool for holding a key, speaking, and pasting
local transcription into a terminal. It is designed for long prompts in Codex
CLI. It never presses Enter.

## Architecture

```text
Page Down held -> default microphone -> resident Moonshine Medium Streaming
                                      `-> partials processed while speaking

Page Down up   -> drain final phrase -> close microphone -> xclip -> xdotool
                                                        `-> no Enter

Page Up held   -> pw-record -> private WAV -> resident small.en worker

Turbo remains available through bin/ptt-dictation as the batch-quality fallback.
```

- Physical Page Down uses Moonshine's 245-million-parameter English Medium
  Streaming model. A private worker keeps only the neural model resident. Each
  hold creates a fresh microphone stream and each release drains and closes it,
  so the audio device is not kept open while idle. No Page Down audio file is
  created.
- Moonshine performs recognition throughout the recording and commits immutable
  lines at pauses. Mutable partial hypotheses remain internal; only the combined
  final text is pasted after release.
- `pw-record` remains the native PipeWire recorder for the batch Whisper paths.
  With no explicit target it follows PipeWire's current default source.
- faster-whisper runs `large-v3-turbo` and `small.en` through CTranslate2 on the
  CPU with INT8. This machine's Radeon 860M is not exposed as a supported
  CTranslate2 GPU, so the eight physical Ryzen CPU cores remain the reliable
  Whisper backend.
- Physical Page Up is a controlled speed/accuracy experiment using the
  English-only `small.en` model. It has a separate Unix socket, process, state,
  and logs, so both models can remain resident simultaneously. Recording state
  is still shared: only one microphone session can exist at a time, and a
  release event from the other hotkey is ignored.
- The Page Down model worker is warmed by i3 at login/reload. If it is stopped,
  stale, or its configuration changes, the controller recreates it. Turbo and
  Small retain their direct-transcription fallback.
- `xclip` owns the X11 clipboard and `xdotool` sends one `Ctrl+Shift+V`. This is
  much more reliable in terminals than simulating every character.
- The X11 window focused when recording starts is remembered and refocused before
  paste. Notifications do not redirect the output.
- A locked state file prevents duplicate recorders and duplicate `stop` actions.
  A new recording is refused while the previous recording is transcribing.
- Batch audio exists only under `$XDG_RUNTIME_DIR/ptt-dictation/` and is removed
  after success, failure, or cancellation. Moonshine streams from memory and
  does not create temporary audio.
- Logs live in `~/.local/state/ptt-dictation/`. Whisper models live under
  `~/.cache/ptt-dictation/`; Moonshine uses `~/.cache/moonshine_voice/`.
- The completion notification reports recording length, release-to-result
  latency, transcribed word count, and speaking words per minute (WPM). The WPM
  uses finalized audio duration; release latency runs from the i3 `stop` command
  until paste has been sent (or the clipboard fallback is ready).

## Dependencies

Runtime Fedora packages:

- `pipewire-utils` (`pw-record`)
- `xclip`
- `xdotool`
- `libnotify` (`notify-send`)
- `httpd-core` (`rotatelogs`, used only as a lightweight bounded-log sink)
- `portaudio` (microphone capture used by Moonshine's Python binding)

All six are already installed on this Fedora 43 machine. `ffmpeg`, `arecord`,
and `parec` were inspected but are not needed. No sudo installation was performed.

Python dependencies are locked in `uv.lock`; the direct dependencies are:

- `faster-whisper>=1.2.1,<2`
- `moonshine-voice>=0.1.3`

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
ln -s /home/pt/dev/dotfiles/push-to-talk/bin/ptt-dictation-small ~/.local/bin/ptt-dictation-small
ln -s /home/pt/dev/dotfiles/push-to-talk/bin/ptt-dictation-moonshine ~/.local/bin/ptt-dictation-moonshine
ptt-dictation-moonshine doctor
```

This dotfiles repository also exposes `bin/ptt-dictation`, so from
`/home/pt/dev/dotfiles` the relative command works as written.

The first Turbo transcription downloads about 1.6 GB of model data to
`~/.cache/ptt-dictation/`. Later runs reuse it. The launcher disables Hugging
Face's optional Xet transfer path because it stalled on this host; ordinary HTTP
completed successfully.

Page Up's first use must separately download `small.en`. Warm it before the
first keyboard test so model download time is not mistaken for transcription
latency:

```bash
bin/ptt-dictation-small worker-start
bin/ptt-dictation-small worker-status
```

Moonshine Medium Streaming downloads about 293 MB into
`~/.cache/moonshine_voice/`. Warm and verify it with:

```bash
bin/ptt-dictation-moonshine worker-start
bin/ptt-dictation-moonshine worker-status
```

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

Page Down adds the tracked `config.moonshine.toml` overlay:

```toml
[moonshine]
language = "en"
model_arch = "medium-streaming"
update_interval_seconds = 0.5
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

`config.small.toml` is the tracked Page Up overlay. Its launcher sets
`PTT_PROFILE=small` and `PTT_INSTANCE=small`; this changes the model to
`small.en` and gives it isolated worker/log paths while inheriting every other
setting from `config.toml`.

`config.moonshine.toml` works the same way with `PTT_PROFILE=moonshine` and an
isolated Moonshine socket, process state, and logs. The global session lock is
shared across all three backends.

The worker has no artificial RAM cap. On this machine it measured about 976 MiB
immediately after loading and about 1.1 GiB after transcription, comfortably
within the available memory. Turbo remains the batch-quality fallback rather
than the physical Page Down backend.

### What beam size means

Whisper generates text token by token. `beam_size = 5` keeps and compares up to
five promising token sequences while decoding instead of committing immediately
to the single highest-scoring next token. This can help with ambiguous speech,
names, and technical wording. A beam size of 1 is greedy decoding and may be
faster, but it can reduce accuracy. Beam size is not a model-size or RAM limit;
this project intentionally leaves it at 5.

## Commands

```bash
bin/ptt-dictation-moonshine start
bin/ptt-dictation-moonshine stop
bin/ptt-dictation-moonshine cancel
bin/ptt-dictation-moonshine status
bin/ptt-dictation-moonshine doctor
bin/ptt-dictation-moonshine worker-start
bin/ptt-dictation-moonshine worker-status
bin/ptt-dictation-moonshine worker-stop

bin/ptt-dictation start
bin/ptt-dictation stop
bin/ptt-dictation cancel
bin/ptt-dictation status
bin/ptt-dictation toggle
bin/ptt-dictation doctor
bin/ptt-dictation worker-start
bin/ptt-dictation worker-status
bin/ptt-dictation worker-stop
bin/ptt-dictation-small worker-start
bin/ptt-dictation-small worker-status
bin/ptt-dictation-small worker-stop
```

- The `ptt-dictation-moonshine` launcher is the physical Page Down backend.
  `start` opens the default microphone and streams recognition in the resident
  worker; `stop` drains the final phrase, closes the microphone, copies, and
  pastes without Enter.
- `stop --no-paste` prints the transcription instead.
- `cancel` closes the microphone and discards the accumulated streaming text.
- Moonshine `worker-start` loads Medium Streaming but does not open the
  microphone. i3 runs it automatically at login and reload.
- `worker-status` shows the phase, PID, and current resident memory.
- `worker-stop` releases the resident model memory. The next recording starts it
  again automatically.
- The plain `ptt-dictation` launcher remains the Turbo batch backend and retains
  `toggle`, file transcription, microphone-test, and paste-test commands.
- The `ptt-dictation-small` launcher supports the same commands but operates on
  the Page Up `small.en` worker. It does not replace or stop the Turbo worker.

## Exact i3 binding

Kanata taps virtual F13/F14 for physical Page Down and F15/F16 for physical Page
Up. On this X11 keyboard map those appear as raw keycodes 191-194 without
keysyms, so these bindings are installed in
`/home/pt/dev/dotfiles/i3config`:

```i3config
set $ptt /home/pt/dev/dotfiles/push-to-talk/bin/ptt-dictation-moonshine
exec_always --no-startup-id $ptt worker-start
bindcode 191 exec --no-startup-id $ptt start
bindcode 192 exec --no-startup-id $ptt stop

set $ptt_small /home/pt/dev/dotfiles/push-to-talk/bin/ptt-dictation-small
bindcode 193 exec --no-startup-id $ptt_small start
bindcode 194 exec --no-startup-id $ptt_small stop
```

Then reload i3:

```bash
sudo systemctl restart kanata.service
i3-msg reload
```

The Kanata service needs the first command because it is a system service. This
is only a service restart; it installs no package. On the next login/reboot,
Kanata and i3 load these tracked configurations automatically. The model workers
are recreated automatically; i3 proactively warms Moonshine so Page Down starts
capturing immediately.

### Kanata

Kanata is currently a root system service on this machine. Do not run the
dictation command directly from Kanata: it would inherit the wrong user,
`DISPLAY`, clipboard, cache, and state directories.

The physical `pgdn` and `pgup` keys are included in `defsrc` on every layer.
Physical Page Down taps F13/F14 for Moonshine; physical Page Up taps F15/F16 for
Small. i3 maps F13/F14 to Moonshine and F15/F16 to Small with the correct X11
user environment. The separate `pgdn` and `pgup` actions on the navigation
layer are unchanged, so those layer combinations still produce normal
navigation keys.

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

Test the streaming backend manually:

```bash
bin/ptt-dictation-moonshine worker-start
bin/ptt-dictation-moonshine start
# Speak a sentence, then:
bin/ptt-dictation-moonshine stop --no-paste
```

Focus Codex CLI, hold the physical Page Down key, dictate, and release it.
The result should appear at the prompt without being submitted.

### 5. Compare Turbo and Small fairly

Do not compare them from two separate spoken attempts; wording and audio will
differ. Record one 20-60 second sample, warm both workers, and feed that exact
WAV to both:

```bash
bin/ptt-dictation record-test --seconds 30 --keep /tmp/ptt-ab.wav
bin/ptt-dictation worker-start
bin/ptt-dictation-small worker-start

time bin/ptt-dictation transcribe-file /tmp/ptt-ab.wav
time bin/ptt-dictation-small transcribe-file /tmp/ptt-ab.wav
unlink /tmp/ptt-ab.wav
```

Repeat each transcription once before judging speed; the first request includes
filesystem/cache warm-up. Compare technical terms, punctuation, names, and
omissions—not only elapsed time. These commands remain useful for comparing the
two batch Whisper fallbacks; physical Page Down now uses Moonshine.

## Moonshine streaming implementation

The Page Up experiment is still ordinary faster-whisper: it records the whole
utterance and transcribes only after release. A smaller model can reduce compute
time, but it cannot remove that architecture's fixed finalize/encode/decode
latency.

Physical Page Down now uses Moonshine's Gen 2 Medium Streaming model. It caches
encoded audio and decoder state instead of reprocessing the complete recording.
The `moonshine-voice` package uses an ONNX Runtime/C++ core and emits mutable
partials plus immutable completed lines. The published accuracy numbers are
vendor benchmarks, so Turbo remains available when exact technical wording is
more important than release latency.

Integration should retain the reliable X11 tail of this project:

```text
key held -> fresh microphone stream -> resident Moonshine -> internal partials
release  -> drain queued audio -> finalize last line -> close microphone
         -> xclip -> one xdotool paste -> no Enter
```

Do not paste partial hypotheses into Codex CLI: streaming recognizers revise
earlier words, while terminal editing has no dependable cross-application way
to replace arbitrary prior text. Streaming should happen internally; clipboard
insertion should happen once, only after the final result.

The model stays resident, but the microphone does not. The worker creates a new
Moonshine `MicTranscriber` backed by the resident model on press, then calls
`stop()` and `close()` on release. This both guarantees final-line delivery and
releases the PortAudio device while idle.

- Moonshine official implementation and model table:
  <https://github.com/moonshine-ai/moonshine>
- Moonshine Streaming paper: <https://arxiv.org/abs/2602.12241>
- `whisper.cpp`'s official stream example calls itself a naive sliding-window
  implementation, so it is not a better next step for eliminating overhead:
  <https://github.com/ggml-org/whisper.cpp/tree/master/examples/stream>
- `sherpa-onnx` is the runner-up: mature CPU/ONNX streaming and endpointing, but
  it would require a separate accuracy evaluation for long technical prompts:
  <https://k2-fsa.github.io/sherpa/onnx/python/index.html>

The automated development tests verify Moonshine line collection, duplicate
line suppression, cross-backend release isolation, the fast-release/warm-up
race, and a complete mocked start/stream/stop/paste cycle. A cached-model test
also verified real chunked Medium Streaming events and final-line delivery.

The earlier batch development test verified duplicate `start`, live `status`, real
default-microphone recording, `large-v3-turbo` transcription, cleanup, and the
return to `idle`. A separate disposable kitty/tmux test verified actual X11
clipboard insertion without Enter and restored both focus and clipboard.

The earlier Whisper resident-worker tests additionally verified cold startup,
two requests on the same PID, clean shutdown, automatic recreation after an
unexpected exit, and direct fallback after a simulated worker failure.

## Diagnostics

Run the built-in check first:

```bash
bin/ptt-dictation-moonshine doctor
bin/ptt-dictation-moonshine status
bin/ptt-dictation-moonshine worker-status
bin/ptt-dictation doctor
bin/ptt-dictation status
bin/ptt-dictation worker-status
bin/ptt-dictation-small worker-status
```

Watch controller and component logs:

```bash
tail -f ~/.local/state/ptt-dictation/ptt-moonshine.log
tail -f ~/.local/state/ptt-dictation/moonshine-worker.log
tail -f ~/.local/state/ptt-dictation/ptt.log
tail -f ~/.local/state/ptt-dictation/recorder.log
tail -f ~/.local/state/ptt-dictation/clipboard.log
tail -f ~/.local/state/ptt-dictation/worker.log
tail -f ~/.local/state/ptt-dictation/ptt-small.log
tail -f ~/.local/state/ptt-dictation/worker-small.log
```

The log files are all under `~/.local/state/ptt-dictation/`:

- `ptt-moonshine.log` is the main Page Down log. It records session lifecycle,
  finalization latency, maximum streaming-line latency, text size, WPM, paste
  delivery, warnings, and Python tracebacks.
- `moonshine-worker.log` captures native Moonshine, model-loading, PortAudio,
  and uncaught worker-process output.
- `ptt.log` is the main log. It records start/stop, Whisper results, paste
  delivery, warnings, Python tracebacks, and one `Dictation metrics` line per
  completed recording. That line includes recording duration,
  release-to-result latency, word count, WPM, and whether automatic paste
  succeeded. Usually, this is the first file to inspect.
- `recorder.log` contains errors written by `pw-record` and PipeWire.
- `clipboard.log` contains errors written by `xclip`.
- `worker.log` captures uncaught startup failures from the resident Whisper
  process. Normal worker lifecycle and request timings are recorded in
  `ptt.log`.
- `ptt-small.log` and `worker-small.log` are the corresponding Page Up files.

`ptt.log` rotates at 1 MB and retains three backups. Each component log retains
its current 1 MB file and one 1 MB backup, including output produced during one
long-running process. The complete log directory is therefore bounded to
approximately 22 MB with all three model profiles (plus a small allowance for
the final write at rotation).

An empty `recorder.log` or `clipboard.log` is normal when that component has not
reported an error.

To inspect recent failures without following the files continuously:

```bash
tail -n 100 ~/.local/state/ptt-dictation/ptt-moonshine.log
tail -n 100 ~/.local/state/ptt-dictation/moonshine-worker.log
tail -n 100 ~/.local/state/ptt-dictation/ptt.log
grep -E ' (ERROR|WARNING) ' ~/.local/state/ptt-dictation/ptt.log | tail -n 30
journalctl -u kanata.service -n 100 --no-pager
```

### Microphone failures

```bash
pactl info | grep 'Default Source'
wpctl status
wpctl get-volume @DEFAULT_AUDIO_SOURCE@
bin/ptt-dictation-moonshine doctor
bin/ptt-dictation record-test --seconds 3 --keep /tmp/ptt-mic-test.wav
```

If the WAV is silent, select/unmute the intended source with `wpctl` or the
desktop audio controls, then repeat `record-test`. `recorder.log` contains
PipeWire connection errors. Page Down uses PortAudio through Moonshine rather
than `pw-record`; inspect `moonshine-worker.log` for its device errors. The
`doctor` device probe has a three-second timeout so diagnostics cannot hang.

### Transcription failures or slowness

```bash
du -sh ~/.cache/moonshine_voice
bin/ptt-dictation-moonshine worker-status
tail -n 100 ~/.local/state/ptt-dictation/ptt-moonshine.log
tail -n 100 ~/.local/state/ptt-dictation/moonshine-worker.log
du -sh ~/.cache/ptt-dictation
bin/ptt-dictation doctor
bin/ptt-dictation worker-status
tail -n 100 ~/.local/state/ptt-dictation/ptt.log
tail -n 100 ~/.local/state/ptt-dictation/worker.log
```

- A first-run network failure affects only the model download; retry the command.
- Moonshine logs `finalization_seconds`, `max_line_latency_ms`, and complete
  release-to-result time separately. For a long recording, finalization should
  depend mainly on the last active phrase rather than total recording length.
- If Page Down's worker appears stale, run
  `bin/ptt-dictation-moonshine worker-stop` followed by `worker-start`.
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

1. Run `bin/ptt-dictation-moonshine cancel` if Page Down is recording, then
   `bin/ptt-dictation-moonshine worker-stop`,
   `bin/ptt-dictation cancel`,
   `bin/ptt-dictation worker-stop` and
   `bin/ptt-dictation-small worker-stop`.
2. Remove both i3 binding blocks shown above and run `i3-msg reload`.
3. Remove the Kanata F13-F16 push-to-talk mappings.
4. Remove generated data and the project:

```bash
cd /home/pt/dev/dotfiles
unlink ~/.local/bin/ptt-dictation
unlink ~/.local/bin/ptt-dictation-moonshine
unlink ~/.local/bin/ptt-dictation-small
unlink ~/bin/ptt-dictation
unlink /home/pt/dev/dotfiles/bin/ptt-dictation
unlink /home/pt/dev/dotfiles/bin/ptt-dictation-moonshine
unlink /home/pt/dev/dotfiles/bin/ptt-dictation-small
rm -rf push-to-talk/.venv
rm -rf ~/.cache/ptt-dictation ~/.cache/moonshine_voice ~/.local/state/ptt-dictation
rm -rf /run/user/$(id -u)/ptt-dictation
git rm -r push-to-talk
```

If the project has not been committed, replace the final `git rm` with
`rm -rf push-to-talk`. Review those paths before running the cleanup commands.
