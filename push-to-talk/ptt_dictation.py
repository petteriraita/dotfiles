#!/usr/bin/env python3
"""Push-to-talk recording, local Whisper transcription, and X11 paste."""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import tomllib
import uuid
import wave


APP_NAME = "ptt-dictation"
PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = PROJECT_DIR / "config.toml"
STATE_HOME = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / APP_NAME
RUNTIME_HOME = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/{APP_NAME}-{os.getuid()}")) / APP_NAME
STATE_FILE = RUNTIME_HOME / "session.json"
LOCK_FILE = RUNTIME_HOME / "control.lock"
LOG_FILE = STATE_HOME / "ptt.log"


def setup_directories() -> None:
    STATE_HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    RUNTIME_HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(STATE_HOME, 0o700)
    os.chmod(RUNTIME_HOME, 0o700)


def setup_logging() -> logging.Logger:
    setup_directories()
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


LOG = setup_logging()


def deep_merge(base: dict, overlay: dict) -> dict:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    config_path = Path(os.environ.get("PTT_CONFIG", DEFAULT_CONFIG)).expanduser()
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    local_path = PROJECT_DIR / "config.local.toml"
    if local_path.exists() and "PTT_CONFIG" not in os.environ:
        with local_path.open("rb") as handle:
            config = deep_merge(config, tomllib.load(handle))
    return config


def run_quiet(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        **kwargs,
    )


def notify(config: dict, summary: str, body: str = "", urgency: str = "normal") -> None:
    settings = config["notifications"]
    if not settings.get("enabled", True):
        return
    command = settings.get("command", "notify-send")
    if not shutil.which(command):
        LOG.warning("Notification command is unavailable: %s", command)
        return
    try:
        result = run_quiet(
            [command, "--app-name", APP_NAME, "--urgency", urgency, summary, body],
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        LOG.warning("Notification failed: %s", exc)
        return
    if result.returncode:
        LOG.warning("Notification failed: %s", result.stderr.strip())


class ControlLock:
    def __enter__(self):
        setup_directories()
        self.handle = LOCK_FILE.open("a+")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


def process_start_ticks(pid: int) -> int | None:
    try:
        # Field 22 is starttime; account for a process name containing spaces.
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return int(fields[19])
    except (FileNotFoundError, PermissionError, ValueError, IndexError):
        return None


def process_matches(pid: int, expected_ticks: int | None) -> bool:
    ticks = process_start_ticks(pid)
    return ticks is not None and (expected_ticks is None or ticks == expected_ticks)


def read_state() -> dict | None:
    try:
        return json.loads(STATE_FILE.read_text())
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as exc:
        LOG.error("Invalid session state: %s", exc)
        return None


def write_state(state: dict) -> None:
    temporary = RUNTIME_HOME / f"session.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, STATE_FILE)


def safe_audio_path(value: str) -> Path:
    path = Path(value).resolve()
    if RUNTIME_HOME.resolve() not in path.parents or path.suffix != ".wav":
        raise RuntimeError(f"Refusing unsafe runtime audio path: {path}")
    return path


def remove_session_files(state: dict | None) -> None:
    if state and state.get("audio_path"):
        try:
            safe_audio_path(state["audio_path"]).unlink(missing_ok=True)
        except (OSError, RuntimeError) as exc:
            LOG.warning("Could not remove session audio: %s", exc)
    STATE_FILE.unlink(missing_ok=True)


def active_window_id(config: dict) -> str | None:
    command = config["paste"].get("xdotool_command", "xdotool")
    if not os.environ.get("DISPLAY") or not shutil.which(command):
        return None
    try:
        result = run_quiet([command, "getactivewindow"], timeout=3)
    except (OSError, subprocess.TimeoutExpired) as exc:
        LOG.warning("Could not capture active X11 window: %s", exc)
        return None
    if result.returncode == 0 and result.stdout.strip().isdigit():
        return result.stdout.strip()
    LOG.warning("Could not capture active X11 window: %s", result.stderr.strip())
    return None


def start_recording(config: dict) -> int:
    recording = config["recording"]
    recorder = recording.get("command", "pw-record")
    if not shutil.which(recorder):
        raise RuntimeError(f"Recorder not found: {recorder}")

    with ControlLock():
        existing = read_state()
        if existing:
            owner_pid = int(existing.get("owner_pid", existing.get("recorder_pid", 0)))
            owner_ticks = existing.get("owner_start_ticks", existing.get("recorder_start_ticks"))
            if process_matches(owner_pid, owner_ticks):
                LOG.info("Ignoring duplicate start; phase=%s", existing.get("phase"))
                return 0
            LOG.warning("Cleaning stale session state")
            remove_session_files(existing)

        session_id = uuid.uuid4().hex
        audio_path = RUNTIME_HOME / f"recording-{session_id}.wav"
        command = [
            recorder,
            "--rate", str(recording.get("sample_rate", 16000)),
            "--channels", str(recording.get("channels", 1)),
            "--format", str(recording.get("sample_format", "s16")),
            str(audio_path),
        ]
        recorder_log = (STATE_HOME / "recorder.log").open("ab", buffering=0)
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=recorder_log,
                start_new_session=True,
            )
        finally:
            recorder_log.close()

        state = {
            "session_id": session_id,
            "phase": "recording",
            "audio_path": str(audio_path),
            "recorder_pid": process.pid,
            "recorder_start_ticks": process_start_ticks(process.pid),
            "owner_pid": process.pid,
            "owner_start_ticks": process_start_ticks(process.pid),
            "target_window": active_window_id(config),
            "started_at": time.time(),
        }
        write_state(state)

    time.sleep(0.08)
    if process.poll() is not None:
        with ControlLock():
            remove_session_files(state)
        raise RuntimeError(f"{recorder} exited immediately; see {STATE_HOME / 'recorder.log'}")

    LOG.info("Recording started: pid=%s session=%s", process.pid, session_id)
    notify(config, "Dictation: recording", "Release the shortcut to transcribe")
    return 0


def terminate_recorder(state: dict, timeout: float) -> None:
    pid = int(state["recorder_pid"])
    ticks = state.get("recorder_start_ticks")
    if not process_matches(pid, ticks):
        LOG.warning("Recorder was already stopped: pid=%s", pid)
        return
    try:
        os.killpg(pid, signal.SIGINT)
    except ProcessLookupError:
        return

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and process_matches(pid, ticks):
        time.sleep(0.05)
    if process_matches(pid, ticks):
        LOG.warning("Recorder did not stop after SIGINT; sending SIGTERM")
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        time.sleep(0.25)
    if process_matches(pid, ticks):
        LOG.error("Recorder did not stop after SIGTERM; sending SIGKILL")
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as audio:
            return audio.getnframes() / float(audio.getframerate())
    except (wave.Error, EOFError, OSError) as exc:
        raise RuntimeError(f"Recorded WAV is invalid: {exc}") from exc


def transcribe_audio(config: dict, audio_path: Path) -> tuple[str, dict]:
    from faster_whisper import WhisperModel

    settings = config["whisper"]
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / APP_NAME
    cache_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    language = settings.get("language") or None
    LOG.info(
        "Loading model=%s device=%s compute_type=%s",
        settings["model"], settings["device"], settings["compute_type"],
    )
    model = WhisperModel(
        settings["model"],
        device=settings.get("device", "cpu"),
        compute_type=settings.get("compute_type", "int8"),
        cpu_threads=int(settings.get("cpu_threads", 0)),
        num_workers=int(settings.get("num_workers", 1)),
        download_root=str(cache_root),
    )
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=int(settings.get("beam_size", 5)),
        vad_filter=bool(settings.get("vad_filter", True)),
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=True,
    )
    text = "".join(segment.text for segment in segments).strip()
    metadata = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
    }
    return text, metadata


def set_clipboard(config: dict, text: str) -> None:
    paste = config["paste"]
    clipboard = paste.get("clipboard_command", "xclip")
    if not shutil.which(clipboard):
        raise RuntimeError(f"Required clipboard command not found: {clipboard}")
    if not os.environ.get("DISPLAY"):
        raise RuntimeError("DISPLAY is unset; cannot access the X11 clipboard")

    # xclip intentionally stays alive while it owns the X11 selection. Do not
    # use subprocess.run(): waiting for it would deadlock until ownership moves.
    clipboard_log = (STATE_HOME / "clipboard.log").open("ab", buffering=0)
    try:
        owner = subprocess.Popen(
            [clipboard, "-selection", "clipboard", "-in"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=clipboard_log,
            start_new_session=True,
        )
        assert owner.stdin is not None
        owner.stdin.write(text.encode("utf-8"))
        owner.stdin.close()
        owner.stdin = None
    finally:
        clipboard_log.close()
    time.sleep(0.05)
    if owner.poll() not in (None, 0):
        raise RuntimeError(f"xclip failed; see {STATE_HOME / 'clipboard.log'}")


def copy_and_paste(config: dict, text: str, target_window: str | None) -> None:
    paste = config["paste"]
    xdotool = paste.get("xdotool_command", "xdotool")
    if not shutil.which(xdotool):
        raise RuntimeError(f"Required paste command not found: {xdotool}")
    set_clipboard(config, text)

    time.sleep(max(0, int(paste.get("delay_ms", 100))) / 1000)
    if paste.get("focus_original_window", True) and target_window:
        focused = run_quiet([xdotool, "windowactivate", "--sync", target_window], timeout=5)
        if focused.returncode:
            LOG.warning("Could not refocus window %s: %s", target_window, focused.stderr.strip())
    result = run_quiet(
        [xdotool, "key", "--clearmodifiers", str(paste.get("hotkey", "ctrl+shift+v"))],
        timeout=5,
    )
    if result.returncode:
        raise RuntimeError(f"xdotool paste failed: {result.stderr.strip()}")


def finish_session(config: dict, no_paste: bool = False) -> int:
    with ControlLock():
        state = read_state()
        if not state:
            LOG.info("Ignoring stop; no recording is active")
            return 0
        if state.get("phase") != "recording":
            LOG.info("Ignoring duplicate stop; phase=%s", state.get("phase"))
            return 0
        state["phase"] = "transcribing"
        state["owner_pid"] = os.getpid()
        state["owner_start_ticks"] = process_start_ticks(os.getpid())
        write_state(state)

    audio_path = safe_audio_path(state["audio_path"])
    try:
        terminate_recorder(state, float(config["recording"].get("stop_timeout_seconds", 5)))
        duration = wav_duration(audio_path)
        minimum = float(config["recording"].get("minimum_seconds", 0.25))
        if duration < minimum:
            raise RuntimeError(f"Recording was too short ({duration:.2f}s; minimum {minimum:.2f}s)")

        LOG.info("Recording stopped: %.2fs; transcribing %s", duration, audio_path)
        notify(config, "Dictation: transcribing", f"Processing {duration:.1f} seconds locally")
        text, metadata = transcribe_audio(config, audio_path)
        if not text:
            raise RuntimeError("Whisper returned an empty transcription")
        LOG.info("Transcription complete: chars=%s metadata=%s", len(text), metadata)
        if no_paste:
            print(text)
        else:
            copy_and_paste(config, text, state.get("target_window"))
        notify(config, "Dictation complete", f"Pasted {len(text)} characters" if not no_paste else text[:100])
        return 0
    finally:
        audio_path.unlink(missing_ok=True)
        with ControlLock():
            current = read_state()
            if current and current.get("session_id") == state.get("session_id"):
                STATE_FILE.unlink(missing_ok=True)


def cancel_session(config: dict) -> int:
    with ControlLock():
        state = read_state()
        if not state:
            print("idle")
            return 0
        if state.get("phase") != "recording":
            raise RuntimeError(f"Cannot cancel while session is {state.get('phase')}")
        state["phase"] = "canceling"
        state["owner_pid"] = os.getpid()
        state["owner_start_ticks"] = process_start_ticks(os.getpid())
        write_state(state)

    try:
        terminate_recorder(state, float(config["recording"].get("stop_timeout_seconds", 5)))
        LOG.info("Recording canceled: session=%s", state.get("session_id"))
        notify(config, "Dictation canceled", "Recording discarded")
        print("canceled")
        return 0
    finally:
        with ControlLock():
            remove_session_files(state)


def record_test(config: dict, seconds: float, keep: Path | None) -> int:
    if seconds <= 0:
        raise RuntimeError("Test duration must be positive")
    recording = config["recording"]
    recorder = recording.get("command", "pw-record")
    if not shutil.which(recorder):
        raise RuntimeError(f"Recorder not found: {recorder}")
    with ControlLock():
        if read_state():
            raise RuntimeError("Cannot run a microphone test while a dictation session exists")
    test_path = RUNTIME_HOME / f"microphone-test-{uuid.uuid4().hex}.wav"
    command = [
        recorder,
        "--rate", str(recording.get("sample_rate", 16000)),
        "--channels", str(recording.get("channels", 1)),
        "--format", str(recording.get("sample_format", "s16")),
        str(test_path),
    ]
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        time.sleep(seconds)
        if process.poll() is not None:
            error = process.stderr.read().decode(errors="replace") if process.stderr else ""
            raise RuntimeError(f"Recorder exited during test: {error.strip()}")
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=float(recording.get("stop_timeout_seconds", 5)))
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        duration = wav_duration(test_path)
        size = test_path.stat().st_size
        print(f"microphone_ok=true duration={duration:.2f}s bytes={size}")
        if keep:
            destination = keep.expanduser().resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            test_path.replace(destination)
            print(f"kept={destination}")
        return 0
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        test_path.unlink(missing_ok=True)


def status() -> int:
    with ControlLock():
        state = read_state()
        if not state:
            print("idle")
            return 1
        owner_pid = int(state.get("owner_pid", 0))
        if process_matches(owner_pid, state.get("owner_start_ticks")):
            print(f"{state.get('phase', 'unknown')} (session {state.get('session_id')}, pid {owner_pid})")
            return 0
        print("stale")
        return 2


def doctor(config: dict) -> int:
    required = [
        config["recording"].get("command", "pw-record"),
        config["paste"].get("clipboard_command", "xclip"),
        config["paste"].get("xdotool_command", "xdotool"),
    ]
    if config["notifications"].get("enabled", True):
        required.append(config["notifications"].get("command", "notify-send"))
    failed = False
    for command in required:
        path = shutil.which(command)
        print(f"{command}: {path or 'MISSING'}")
        failed |= path is None
    print(f"DISPLAY: {os.environ.get('DISPLAY') or 'UNSET'}")
    print(f"config: {os.environ.get('PTT_CONFIG', DEFAULT_CONFIG)}")
    print(f"runtime: {RUNTIME_HOME}")
    print(f"log: {LOG_FILE}")
    try:
        import faster_whisper
        import ctranslate2
        print(f"faster-whisper: {faster_whisper.__version__}")
        print(f"CTranslate2: {ctranslate2.__version__}")
        print(f"CTranslate2 CPU compute types: {sorted(ctranslate2.get_supported_compute_types('cpu'))}")
    except ImportError as exc:
        print(f"Python dependency missing: {exc}")
        failed = True
    return int(failed)


def transcribe_file(config: dict, path: Path, paste: bool) -> int:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"Audio file does not exist: {path}")
    target = active_window_id(config) if paste else None
    text, metadata = transcribe_audio(config, path)
    if not text:
        raise RuntimeError("Whisper returned an empty transcription")
    print(text)
    LOG.info("File transcription complete: path=%s metadata=%s", path, metadata)
    if paste:
        copy_and_paste(config, text, target)
    return 0


def paste_test(config: dict, text: str, clipboard_only: bool) -> int:
    target = active_window_id(config)
    if clipboard_only:
        set_clipboard(config, text)
    else:
        copy_and_paste(config, text, target)
    print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("start", help="start recording; duplicate starts are ignored")
    stop_parser = subparsers.add_parser("stop", help="stop, transcribe, and paste")
    stop_parser.add_argument("--no-paste", action="store_true", help="print transcription instead")
    subparsers.add_parser("cancel", help="stop and discard an active recording")
    toggle_parser = subparsers.add_parser("toggle", help="toggle recording for non-hold bindings")
    toggle_parser.add_argument("--no-paste", action="store_true")
    subparsers.add_parser("status", help="show the current controller phase")
    subparsers.add_parser("doctor", help="check commands, display, and Python dependencies")
    transcribe_parser = subparsers.add_parser("transcribe-file", help="transcribe an existing audio file")
    transcribe_parser.add_argument("path", type=Path)
    transcribe_parser.add_argument("--paste", action="store_true")
    paste_parser = subparsers.add_parser("paste-test", help="test clipboard and optional X11 paste")
    paste_parser.add_argument("text", nargs="?", default="Push-to-talk clipboard test")
    paste_parser.add_argument("--clipboard-only", action="store_true")
    record_parser = subparsers.add_parser("record-test", help="test the default microphone without Whisper")
    record_parser.add_argument("--seconds", type=float, default=2.0)
    record_parser.add_argument("--keep", type=Path, help="keep the test WAV at this path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config()
    if args.command == "start":
        return start_recording(config)
    if args.command == "stop":
        return finish_session(config, args.no_paste)
    if args.command == "cancel":
        return cancel_session(config)
    if args.command == "toggle":
        return finish_session(config, args.no_paste) if read_state() else start_recording(config)
    if args.command == "status":
        return status()
    if args.command == "doctor":
        return doctor(config)
    if args.command == "transcribe-file":
        return transcribe_file(config, args.path, args.paste)
    if args.command == "paste-test":
        return paste_test(config, args.text, args.clipboard_only)
    if args.command == "record-test":
        return record_test(config, args.seconds, args.keep)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        LOG.warning("Interrupted")
        raise SystemExit(130)
    except Exception as exc:
        LOG.exception("Command failed")
        try:
            notify(load_config(), "Dictation failed", str(exc), urgency="critical")
        except Exception:
            pass
        print(f"ptt-dictation: {exc}\nSee {LOG_FILE}", file=sys.stderr)
        raise SystemExit(1)
