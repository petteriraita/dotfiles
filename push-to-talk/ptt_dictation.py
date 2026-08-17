#!/usr/bin/env python3
"""Push-to-talk recording, local Whisper transcription, and X11 paste."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import signal
import socket
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
WORKER_SOCKET = RUNTIME_HOME / "whisper.sock"
WORKER_STATE_FILE = RUNTIME_HOME / "worker.json"
WORKER_LOCK_FILE = RUNTIME_HOME / "worker.lock"
WORKER_LOG_FILE = STATE_HOME / "worker.log"


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


class WorkerLock:
    def __enter__(self):
        setup_directories()
        self.handle = WORKER_LOCK_FILE.open("a+")
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


def worker_signature(config: dict) -> str:
    payload = {
        "whisper": config["whisper"],
        "controller_mtime_ns": Path(__file__).stat().st_mtime_ns,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_worker_state() -> dict | None:
    try:
        return json.loads(WORKER_STATE_FILE.read_text())
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as exc:
        LOG.error("Invalid worker state: %s", exc)
        return None


def write_worker_state(state: dict) -> None:
    temporary = RUNTIME_HOME / f"worker.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, WORKER_STATE_FILE)


def remove_worker_files() -> None:
    WORKER_SOCKET.unlink(missing_ok=True)
    WORKER_STATE_FILE.unlink(missing_ok=True)


def worker_is_alive(state: dict | None) -> bool:
    if not state:
        return False
    return process_matches(int(state.get("pid", 0)), state.get("start_ticks"))


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


def terminate_worker_process(state: dict, timeout: float = 3.0) -> None:
    pid = int(state.get("pid", 0))
    ticks = state.get("start_ticks")
    if not process_matches(pid, ticks):
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and process_matches(pid, ticks):
        time.sleep(0.05)
    if process_matches(pid, ticks):
        LOG.warning("Whisper worker did not stop after SIGTERM; sending SIGKILL")
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def ensure_worker(config: dict, wait_until_ready: bool = False) -> bool:
    settings = config.get("worker", {})
    if not settings.get("enabled", True):
        return False

    signature = worker_signature(config)
    state_to_stop = None
    with WorkerLock():
        state = read_worker_state()
        if worker_is_alive(state):
            if state.get("signature") == signature:
                existing = True
            else:
                LOG.info("Restarting Whisper worker because its configuration changed")
                state_to_stop = state
                existing = False
        else:
            if state:
                LOG.warning("Cleaning stale Whisper worker state")
            remove_worker_files()
            existing = False

    if state_to_stop:
        terminate_worker_process(state_to_stop)
        with WorkerLock():
            current = read_worker_state()
            if current and current.get("pid") == state_to_stop.get("pid"):
                remove_worker_files()

    if not existing:
        with WorkerLock():
            # Another controller may have created the replacement while this
            # process waited for an outdated worker to stop.
            state = read_worker_state()
            if worker_is_alive(state) and state.get("signature") == signature:
                existing = True
            else:
                remove_worker_files()
                worker_log = WORKER_LOG_FILE.open("ab", buffering=0)
                try:
                    process = subprocess.Popen(
                        [sys.executable, str(Path(__file__).resolve()), "_worker"],
                        stdin=subprocess.DEVNULL,
                        stdout=worker_log,
                        stderr=worker_log,
                        start_new_session=True,
                    )
                finally:
                    worker_log.close()
                state = {
                    "pid": process.pid,
                    "start_ticks": process_start_ticks(process.pid),
                    "phase": "starting",
                    "signature": signature,
                    "started_at": time.time(),
                }
                write_worker_state(state)
                LOG.info("Whisper worker starting: pid=%s", process.pid)

    if wait_until_ready:
        timeout = float(settings.get("startup_timeout_seconds", 20))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with WorkerLock():
                state = read_worker_state()
                if not worker_is_alive(state):
                    raise RuntimeError(f"Whisper worker exited; see {WORKER_LOG_FILE}")
                if state.get("phase") == "ready" and WORKER_SOCKET.exists():
                    return True
            time.sleep(0.05)
        raise RuntimeError(f"Whisper worker was not ready after {timeout:.1f}s")
    return True


def worker_rpc(config: dict, request: dict, response_timeout: float | None = None) -> dict:
    settings = config.get("worker", {})
    connect_timeout = float(settings.get("startup_timeout_seconds", 20))
    deadline = time.monotonic() + connect_timeout
    connection = None
    try:
        while True:
            candidate = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                candidate.connect(str(WORKER_SOCKET))
                connection = candidate
                break
            except (FileNotFoundError, ConnectionRefusedError):
                candidate.close()
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"Whisper worker socket was unavailable after {connect_timeout:.1f}s"
                    )
                time.sleep(0.05)
        connection.settimeout(
            response_timeout
            if response_timeout is not None
            else float(settings.get("request_timeout_seconds", 300))
        )
        connection.sendall(json.dumps(request).encode("utf-8") + b"\n")
        received = bytearray()
        while not received.endswith(b"\n"):
            chunk = connection.recv(65536)
            if not chunk:
                raise RuntimeError("Whisper worker closed the connection without a response")
            received.extend(chunk)
            if len(received) > 10_000_000:
                raise RuntimeError("Whisper worker response exceeded 10 MB")
        response = json.loads(received)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Whisper worker request failed: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
    if not response.get("ok"):
        raise RuntimeError(response.get("error", "Whisper worker reported an unknown error"))
    return response


def worker_memory_mib(pid: int) -> float | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except (FileNotFoundError, PermissionError, ValueError, IndexError):
        pass
    return None


def worker_status(config: dict) -> int:
    with WorkerLock():
        state = read_worker_state()
        if not worker_is_alive(state):
            print("stopped")
            return 1
        pid = int(state["pid"])
        phase = state.get("phase", "unknown")
        memory = worker_memory_mib(pid)
    detail = f", memory={memory:.0f} MiB" if memory is not None else ""
    print(f"{phase} (pid {pid}{detail})")
    return 0 if phase == "ready" else 2


def worker_start(config: dict) -> int:
    if not config.get("worker", {}).get("enabled", True):
        raise RuntimeError("Whisper worker is disabled in the configuration")
    ensure_worker(config, wait_until_ready=True)
    return worker_status(config)


def worker_stop(config: dict) -> int:
    with WorkerLock():
        state = read_worker_state()
    if not worker_is_alive(state):
        with WorkerLock():
            remove_worker_files()
        print("stopped")
        return 0
    try:
        worker_rpc(config, {"command": "shutdown"}, response_timeout=3)
    except RuntimeError as exc:
        LOG.warning("Graceful Whisper worker shutdown failed: %s", exc)
        terminate_worker_process(state)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and worker_is_alive(state):
        time.sleep(0.05)
    if worker_is_alive(state):
        terminate_worker_process(state)
    with WorkerLock():
        current = read_worker_state()
        if not current or current.get("pid") == state.get("pid"):
            remove_worker_files()
    print("stopped")
    return 0


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

        # Do not publish the session until pw-record has survived its startup
        # window.  The control lock deliberately remains held here: otherwise
        # a fast key release can let `stop` kill the recorder while `start` is
        # still checking it, causing `start` to delete the WAV underneath the
        # transcriber.
        time.sleep(0.08)
        if process.poll() is not None:
            audio_path.unlink(missing_ok=True)
            raise RuntimeError(f"{recorder} exited immediately; see {STATE_HOME / 'recorder.log'}")

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

    LOG.info("Recording started: pid=%s session=%s", process.pid, session_id)
    notify(config, "Dictation: recording", "Release the shortcut to transcribe")
    try:
        ensure_worker(config)
    except Exception as exc:
        # Recording remains usable: stop will retry the worker and ultimately
        # fall back to direct in-process transcription.
        LOG.warning("Could not warm Whisper worker during recording: %s", exc)
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


def load_whisper_model(config: dict):
    from faster_whisper import WhisperModel

    settings = config["whisper"]
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / APP_NAME
    cache_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    LOG.info(
        "Loading model=%s device=%s compute_type=%s",
        settings["model"], settings["device"], settings["compute_type"],
    )
    return WhisperModel(
        settings["model"],
        device=settings.get("device", "cpu"),
        compute_type=settings.get("compute_type", "int8"),
        cpu_threads=int(settings.get("cpu_threads", 0)),
        num_workers=int(settings.get("num_workers", 1)),
        download_root=str(cache_root),
    )


def transcribe_with_model(model, config: dict, audio_path: Path) -> tuple[str, dict]:
    settings = config["whisper"]
    language = settings.get("language") or None
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


def transcribe_audio_direct(config: dict, audio_path: Path) -> tuple[str, dict]:
    LOG.info("Using direct Whisper fallback")
    model = load_whisper_model(config)
    return transcribe_with_model(model, config, audio_path)


def run_worker(config: dict) -> int:
    setup_directories()
    running = [True]

    def request_shutdown(signum, frame) -> None:
        running[0] = False

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    WORKER_SOCKET.unlink(missing_ok=True)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(WORKER_SOCKET))
        os.chmod(WORKER_SOCKET, 0o600)
        server.listen(4)
        server.settimeout(0.5)

        load_started = time.monotonic()
        model = load_whisper_model(config)
        load_seconds = time.monotonic() - load_started
        with WorkerLock():
            state = read_worker_state()
            if state and int(state.get("pid", 0)) == os.getpid():
                state["phase"] = "ready"
                state["ready_at"] = time.time()
                state["model_load_seconds"] = load_seconds
                write_worker_state(state)
        LOG.info("Whisper worker ready: pid=%s load_seconds=%.2f", os.getpid(), load_seconds)

        while running[0]:
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue
            with connection:
                try:
                    received = bytearray()
                    while not received.endswith(b"\n"):
                        chunk = connection.recv(65536)
                        if not chunk:
                            raise RuntimeError("Client closed the request early")
                        received.extend(chunk)
                        if len(received) > 1_000_000:
                            raise RuntimeError("Worker request exceeded 1 MB")
                    request = json.loads(received)
                    command = request.get("command")
                    if command == "ping":
                        response = {"ok": True, "phase": "ready", "pid": os.getpid()}
                    elif command == "shutdown":
                        response = {"ok": True}
                        running[0] = False
                    elif command == "transcribe":
                        audio_path = Path(str(request.get("audio_path", ""))).expanduser().resolve()
                        if not audio_path.is_file():
                            raise RuntimeError(f"Audio file does not exist: {audio_path}")
                        started = time.monotonic()
                        text, metadata = transcribe_with_model(model, config, audio_path)
                        elapsed = time.monotonic() - started
                        LOG.info(
                            "Whisper worker transcription: seconds=%.2f chars=%s path=%s",
                            elapsed,
                            len(text),
                            audio_path,
                        )
                        response = {
                            "ok": True,
                            "text": text,
                            "metadata": metadata,
                            "elapsed_seconds": elapsed,
                        }
                    else:
                        raise RuntimeError(f"Unknown worker command: {command}")
                except Exception as exc:
                    LOG.exception("Whisper worker request failed")
                    response = {"ok": False, "error": str(exc)}
                try:
                    connection.sendall(json.dumps(response).encode("utf-8") + b"\n")
                except (BrokenPipeError, ConnectionResetError):
                    LOG.warning("Whisper worker client disconnected before receiving its response")
        return 0
    finally:
        server.close()
        with WorkerLock():
            state = read_worker_state()
            if not state or int(state.get("pid", 0)) == os.getpid():
                remove_worker_files()
        LOG.info("Whisper worker stopped: pid=%s", os.getpid())


def transcribe_audio(config: dict, audio_path: Path) -> tuple[str, dict]:
    settings = config.get("worker", {})
    if settings.get("enabled", True):
        try:
            ensure_worker(config)
            response = worker_rpc(
                config,
                {"command": "transcribe", "audio_path": str(audio_path)},
            )
            LOG.info(
                "Used resident Whisper worker: elapsed_seconds=%.2f",
                float(response.get("elapsed_seconds", 0)),
            )
            return str(response["text"]), dict(response["metadata"])
        except Exception as exc:
            if not settings.get("fallback_to_direct", True):
                raise
            LOG.warning("Resident Whisper worker failed; using direct fallback: %s", exc)
    return transcribe_audio_direct(config, audio_path)


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


def copy_and_paste(config: dict, text: str, target_window: str | None) -> bool:
    """Copy text and best-effort paste it, returning whether paste was sent.

    Clipboard ownership is established first, so a stale or unresponsive X11
    window can never make the transcription unavailable to the user.
    """
    paste = config["paste"]
    xdotool = paste.get("xdotool_command", "xdotool")
    set_clipboard(config, text)
    if not shutil.which(xdotool):
        LOG.warning("Automatic paste skipped; command is unavailable: %s", xdotool)
        return False

    time.sleep(max(0, int(paste.get("delay_ms", 100))) / 1000)
    if paste.get("focus_original_window", True) and target_window:
        current_window = active_window_id(config)
        if current_window != target_window:
            try:
                # Avoid `--sync`: some X11 applications accept activation but
                # never satisfy xdotool's synchronous focus wait. Verify focus
                # ourselves with a short, bounded poll instead.
                focused = run_quiet([xdotool, "windowactivate", target_window], timeout=2)
            except (OSError, subprocess.TimeoutExpired) as exc:
                LOG.warning(
                    "Automatic paste skipped; could not request focus for window %s: %s",
                    target_window,
                    exc,
                )
                return False
            if focused.returncode:
                LOG.warning(
                    "Automatic paste skipped; could not refocus window %s: %s",
                    target_window,
                    focused.stderr.strip(),
                )
                return False

            deadline = time.monotonic() + max(
                0,
                int(paste.get("focus_timeout_ms", 1000)),
            ) / 1000
            while time.monotonic() < deadline:
                if active_window_id(config) == target_window:
                    break
                time.sleep(0.05)
            else:
                LOG.warning(
                    "Automatic paste skipped; window %s did not receive focus; "
                    "transcription remains on clipboard",
                    target_window,
                )
                return False

    try:
        result = run_quiet(
            [xdotool, "key", "--clearmodifiers", str(paste.get("hotkey", "ctrl+shift+v"))],
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        LOG.warning("Automatic paste failed; transcription remains on clipboard: %s", exc)
        return False
    if result.returncode:
        LOG.warning(
            "Automatic paste failed; transcription remains on clipboard: %s",
            result.stderr.strip(),
        )
        return False
    LOG.info("Paste sent to X11 window=%s chars=%s", target_window or "current", len(text))
    return True


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
            LOG.info(
                "Ignoring short recording: %.2fs (minimum %.2fs)",
                duration,
                minimum,
            )
            notify(config, "Dictation canceled", "Recording was too short")
            return 0

        LOG.info("Recording stopped: %.2fs; transcribing %s", duration, audio_path)
        notify(config, "Dictation: transcribing", f"Processing {duration:.1f} seconds locally")
        text, metadata = transcribe_audio(config, audio_path)
        if not text:
            raise RuntimeError("Whisper returned an empty transcription")
        LOG.info("Transcription complete: chars=%s metadata=%s", len(text), metadata)
        if no_paste:
            print(text)
            pasted = False
        else:
            pasted = copy_and_paste(config, text, state.get("target_window"))
        if no_paste:
            notify(config, "Dictation complete", text[:100])
        elif pasted:
            notify(config, "Dictation complete", f"Pasted {len(text)} characters")
        else:
            notify(
                config,
                "Dictation copied",
                "Automatic paste failed; press Ctrl+Shift+V",
                urgency="critical",
            )
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
    print(f"worker log: {WORKER_LOG_FILE}")
    worker = read_worker_state()
    worker_phase = worker.get("phase", "unknown") if worker_is_alive(worker) else "stopped"
    print(f"worker: {worker_phase}")
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
    subparsers.add_parser("worker-start", help="start and warm the resident Whisper worker")
    subparsers.add_parser("worker-status", help="show resident Whisper worker status")
    subparsers.add_parser("worker-stop", help="stop the resident Whisper worker")
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
    if len(sys.argv) > 1 and sys.argv[1] == "_worker":
        return run_worker(load_config())
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
    if args.command == "worker-start":
        return worker_start(config)
    if args.command == "worker-status":
        return worker_status(config)
    if args.command == "worker-stop":
        return worker_stop(config)
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
