#!/usr/bin/env python3
"""Streaming Moonshine push-to-talk controller for X11."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid


# Import the shared X11, notification, metrics, and global-session machinery as
# a distinct instance. This still uses the same global session.json/control.lock
# as Turbo and Small, preventing simultaneous microphone sessions.
PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("PTT_INSTANCE", "moonshine")
os.environ.setdefault("PTT_PROFILE", "moonshine")
import ptt_dictation as core  # noqa: E402


WORKER_SOCKET = core.RUNTIME_HOME / "moonshine.sock"
WORKER_STATE_FILE = core.RUNTIME_HOME / "moonshine-worker.json"
WORKER_LOCK_FILE = core.RUNTIME_HOME / "moonshine-worker.lock"
WORKER_LOG_FILE = core.STATE_HOME / "moonshine-worker.log"


class WorkerLock:
    def __enter__(self):
        core.setup_directories()
        self.handle = WORKER_LOCK_FILE.open("a+")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


def read_worker_state() -> dict | None:
    try:
        return json.loads(WORKER_STATE_FILE.read_text())
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as exc:
        core.LOG.error("Invalid Moonshine worker state: %s", exc)
        return None


def write_worker_state(state: dict) -> None:
    temporary = core.RUNTIME_HOME / f"moonshine-worker.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, WORKER_STATE_FILE)


def remove_worker_files() -> None:
    WORKER_SOCKET.unlink(missing_ok=True)
    WORKER_STATE_FILE.unlink(missing_ok=True)


def worker_is_alive(state: dict | None) -> bool:
    if not state:
        return False
    return core.process_matches(int(state.get("pid", 0)), state.get("start_ticks"))


def worker_signature(config: dict) -> str:
    payload = {
        "moonshine": config["moonshine"],
        "controller_mtime_ns": Path(__file__).stat().st_mtime_ns,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def terminate_worker(state: dict, timeout: float = 3.0) -> None:
    pid = int(state.get("pid", 0))
    ticks = state.get("start_ticks")
    if not core.process_matches(pid, ticks):
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and core.process_matches(pid, ticks):
        time.sleep(0.05)
    if core.process_matches(pid, ticks):
        core.LOG.warning("Moonshine worker did not stop after SIGTERM; sending SIGKILL")
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def ensure_worker(config: dict, wait_until_ready: bool = False) -> bool:
    signature = worker_signature(config)
    state_to_stop = None
    with WorkerLock():
        state = read_worker_state()
        if worker_is_alive(state):
            if state.get("signature") == signature:
                existing = True
            else:
                state_to_stop = state
                existing = False
        else:
            if state:
                core.LOG.warning("Cleaning stale Moonshine worker state")
            remove_worker_files()
            existing = False

    if state_to_stop:
        core.LOG.info("Restarting Moonshine worker because its configuration changed")
        terminate_worker(state_to_stop)
        with WorkerLock():
            current = read_worker_state()
            if current and current.get("pid") == state_to_stop.get("pid"):
                remove_worker_files()

    if not existing:
        with WorkerLock():
            state = read_worker_state()
            if worker_is_alive(state) and state.get("signature") == signature:
                existing = True
            else:
                remove_worker_files()
                with core.bounded_component_log(WORKER_LOG_FILE) as worker_log:
                    process = subprocess.Popen(
                        [sys.executable, str(Path(__file__).resolve()), "_worker"],
                        stdin=subprocess.DEVNULL,
                        stdout=worker_log,
                        stderr=worker_log,
                        start_new_session=True,
                    )
                state = {
                    "pid": process.pid,
                    "start_ticks": core.process_start_ticks(process.pid),
                    "phase": "starting",
                    "signature": signature,
                    "started_at": time.time(),
                }
                write_worker_state(state)
                core.LOG.info("Moonshine worker starting: pid=%s", process.pid)

    if wait_until_ready:
        timeout = float(config["moonshine"].get("startup_timeout_seconds", 30))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with WorkerLock():
                state = read_worker_state()
                if not worker_is_alive(state):
                    raise RuntimeError(
                        f"Moonshine worker exited; see {WORKER_LOG_FILE}"
                    )
                if state.get("phase") == "ready" and WORKER_SOCKET.exists():
                    return True
            time.sleep(0.05)
        raise RuntimeError(f"Moonshine worker was not ready after {timeout:.1f}s")
    return True


def worker_rpc(
    config: dict, request: dict, response_timeout: float | None = None
) -> dict:
    timeout = float(config["moonshine"].get("startup_timeout_seconds", 30))
    deadline = time.monotonic() + timeout
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
                        f"Moonshine worker socket was unavailable after {timeout:.1f}s"
                    )
                time.sleep(0.05)
        connection.settimeout(
            response_timeout
            if response_timeout is not None
            else float(config["moonshine"].get("request_timeout_seconds", 60))
        )
        connection.sendall(json.dumps(request).encode("utf-8") + b"\n")
        received = bytearray()
        while not received.endswith(b"\n"):
            chunk = connection.recv(65536)
            if not chunk:
                raise RuntimeError("Moonshine worker closed without a response")
            received.extend(chunk)
            if len(received) > 10_000_000:
                raise RuntimeError("Moonshine worker response exceeded 10 MB")
        response = json.loads(received)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Moonshine worker request failed: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
    if not response.get("ok"):
        raise RuntimeError(response.get("error", "Moonshine worker reported an error"))
    return response


class TranscriptCollector:
    """Thread-safe collection of mutable partials and immutable final lines."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self.lines: list[str] = []
            self.line_ids: set[int] = set()
            self.partial = ""
            self.errors: list[str] = []
            self.line_latencies_ms: list[int] = []

    def on_text(self, text: str) -> None:
        with self.lock:
            self.partial = text.strip()

    def on_line(self, line) -> None:
        text = str(line.text).strip()
        line_id = int(line.line_id)
        with self.lock:
            if text and line_id not in self.line_ids:
                self.lines.append(text)
                self.line_ids.add(line_id)
            self.partial = ""
            self.line_latencies_ms.append(int(line.last_transcription_latency_ms))

    def on_error(self, error: BaseException) -> None:
        with self.lock:
            self.errors.append(str(error))

    def snapshot(self) -> dict:
        with self.lock:
            parts = list(self.lines)
            if not parts and self.partial:
                parts.append(self.partial)
            return {
                "text": " ".join(parts).strip(),
                "lines": len(self.lines),
                "partial": self.partial,
                "errors": list(self.errors),
                "max_line_latency_ms": max(self.line_latencies_ms, default=0),
            }


def run_worker(config: dict) -> int:
    from moonshine_voice import (
        MicTranscriber,
        ModelArch,
        Transcriber,
        get_model_for_language,
        string_to_model_arch,
    )

    core.setup_directories()
    settings = config["moonshine"]
    language = str(settings.get("language", "en"))
    arch_name = str(settings.get("model_arch", "medium-streaming"))
    arch: ModelArch = string_to_model_arch(arch_name)
    running = True
    active_mic = None
    active_started = None
    collector = TranscriptCollector()

    def request_shutdown(signum, frame) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    WORKER_SOCKET.unlink(missing_ok=True)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    model = None
    try:
        server.bind(str(WORKER_SOCKET))
        os.chmod(WORKER_SOCKET, 0o600)
        server.listen(4)
        server.settimeout(0.5)

        load_started = time.monotonic()
        model_path, resolved_arch = get_model_for_language(language, arch)
        model = Transcriber(str(model_path), resolved_arch)
        load_seconds = time.monotonic() - load_started
        with WorkerLock():
            state = read_worker_state()
            if state and int(state.get("pid", 0)) == os.getpid():
                state.update(
                    {
                        "phase": "ready",
                        "ready_at": time.time(),
                        "model_load_seconds": load_seconds,
                        "model_arch": arch_name,
                    }
                )
                write_worker_state(state)
        core.LOG.info(
            "Moonshine worker ready: pid=%s model=%s load_seconds=%.2f",
            os.getpid(),
            arch_name,
            load_seconds,
        )

        while running:
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
                            raise RuntimeError("Moonshine worker request exceeded 1 MB")
                    request = json.loads(received)
                    command = request.get("command")
                    if command == "ping":
                        response = {
                            "ok": True,
                            "pid": os.getpid(),
                            "recording": active_mic is not None,
                        }
                    elif command == "start":
                        if active_mic is not None:
                            response = {
                                "ok": True,
                                "pid": os.getpid(),
                                "duplicate": True,
                            }
                        else:
                            collector.reset()
                            mic = (
                                MicTranscriber()
                                .use_transcriber(model)
                                .update_interval(
                                    float(settings.get("update_interval_seconds", 0.5))
                                )
                                .samplerate(int(settings.get("sample_rate", 16000)))
                                .channels(int(settings.get("channels", 1)))
                                .blocksize(int(settings.get("block_size", 1024)))
                                .on_text(collector.on_text)
                                .on_line(collector.on_line)
                                .on_error(collector.on_error)
                            )
                            mic.load()
                            try:
                                mic.start()
                            except Exception:
                                mic.close()
                                raise
                            active_mic = mic
                            active_started = time.monotonic()
                            response = {
                                "ok": True,
                                "pid": os.getpid(),
                                "started_at": time.time(),
                            }
                            core.LOG.info("Moonshine microphone started")
                    elif command in ("stop", "cancel"):
                        if active_mic is None:
                            response = {
                                "ok": True,
                                "text": "",
                                "recording_seconds": 0.0,
                            }
                        else:
                            mic = active_mic
                            started = active_started
                            active_mic = None
                            active_started = None
                            finalize_started = time.monotonic()
                            recording_seconds = (
                                finalize_started - started
                                if started is not None
                                else 0.0
                            )
                            try:
                                mic.stop()
                                snapshot = collector.snapshot()
                            finally:
                                mic.close()
                            finalization_seconds = time.monotonic() - finalize_started
                            if snapshot["errors"]:
                                raise RuntimeError("; ".join(snapshot["errors"]))
                            response = {
                                "ok": True,
                                "text": "" if command == "cancel" else snapshot["text"],
                                "recording_seconds": recording_seconds,
                                "finalization_seconds": finalization_seconds,
                                "lines": snapshot["lines"],
                                "max_line_latency_ms": snapshot["max_line_latency_ms"],
                            }
                            core.LOG.info(
                                "Moonshine microphone %s: recording_seconds=%.2f "
                                "finalization_seconds=%.2f lines=%s chars=%s",
                                "canceled" if command == "cancel" else "stopped",
                                recording_seconds,
                                finalization_seconds,
                                snapshot["lines"],
                                len(snapshot["text"]),
                            )
                    elif command == "shutdown":
                        if active_mic is not None:
                            try:
                                active_mic.stop()
                            finally:
                                active_mic.close()
                            active_mic = None
                            active_started = None
                        response = {"ok": True}
                        running = False
                    else:
                        raise RuntimeError(f"Unknown worker command: {command}")
                except Exception as exc:
                    core.LOG.exception("Moonshine worker request failed")
                    response = {"ok": False, "error": str(exc)}
                try:
                    connection.sendall(json.dumps(response).encode("utf-8") + b"\n")
                except (BrokenPipeError, ConnectionResetError):
                    core.LOG.warning("Moonshine worker client disconnected")
        return 0
    finally:
        if active_mic is not None:
            try:
                active_mic.stop()
            except Exception:
                core.LOG.exception(
                    "Could not stop Moonshine microphone during shutdown"
                )
            finally:
                active_mic.close()
        if model is not None:
            model.close()
        server.close()
        with WorkerLock():
            state = read_worker_state()
            if not state or int(state.get("pid", 0)) == os.getpid():
                remove_worker_files()
        core.LOG.info("Moonshine worker stopped: pid=%s", os.getpid())


def worker_status(config: dict) -> int:
    with WorkerLock():
        state = read_worker_state()
        if not worker_is_alive(state):
            print("stopped")
            return 1
        pid = int(state["pid"])
        phase = state.get("phase", "unknown")
        memory = core.worker_memory_mib(pid)
    recording = False
    if phase == "ready" and WORKER_SOCKET.exists():
        try:
            recording = bool(
                worker_rpc(config, {"command": "ping"}, 2).get("recording")
            )
        except RuntimeError:
            pass
    detail = f", memory={memory:.0f} MiB" if memory is not None else ""
    print(f"{phase} (pid {pid}{detail}, recording={str(recording).lower()})")
    return 0 if phase == "ready" else 2


def worker_start(config: dict) -> int:
    ensure_worker(config, wait_until_ready=True)
    return worker_status(config)


def worker_stop(config: dict) -> int:
    with core.ControlLock():
        session = core.read_state()
        if (
            session
            and session.get("instance") == "moonshine"
            and session.get("phase") in ("starting", "recording", "transcribing")
        ):
            raise RuntimeError("Cancel or finish the active Moonshine session first")
    with WorkerLock():
        state = read_worker_state()
    if not worker_is_alive(state):
        with WorkerLock():
            remove_worker_files()
        print("stopped")
        return 0
    try:
        worker_rpc(config, {"command": "shutdown"}, 5)
    except RuntimeError as exc:
        core.LOG.warning("Graceful Moonshine shutdown failed: %s", exc)
        terminate_worker(state)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and worker_is_alive(state):
        time.sleep(0.05)
    if worker_is_alive(state):
        terminate_worker(state)
    with WorkerLock():
        current = read_worker_state()
        if not current or current.get("pid") == state.get("pid"):
            remove_worker_files()
    print("stopped")
    return 0


def session_owner_alive(state: dict) -> bool:
    owner_pid = int(state.get("owner_pid", 0))
    return core.process_matches(owner_pid, state.get("owner_start_ticks"))


def start_recording(config: dict) -> int:
    session_id = uuid.uuid4().hex
    with core.ControlLock():
        existing = core.read_state()
        if existing:
            if session_owner_alive(existing):
                core.LOG.info(
                    "Ignoring duplicate Moonshine start; phase=%s",
                    existing.get("phase"),
                )
                return 0
            core.LOG.warning("Cleaning stale dictation session")
            core.remove_session_files(existing)
        provisional = {
            "session_id": session_id,
            "instance": "moonshine",
            "phase": "starting",
            "owner_pid": os.getpid(),
            "owner_start_ticks": core.process_start_ticks(os.getpid()),
            "target_window": core.active_window_id(config),
            "started_at": time.time(),
        }
        core.write_state(provisional)

    try:
        ensure_worker(config, wait_until_ready=True)
        with core.ControlLock():
            current = core.read_state()
            if not current or current.get("session_id") != session_id:
                return 0
            if current.get("phase") == "stop_requested":
                core.STATE_FILE.unlink(missing_ok=True)
                core.notify(
                    config,
                    "Dictation canceled",
                    "Moonshine was still warming; hold Page Down again",
                )
                return 0
            response = worker_rpc(config, {"command": "start"}, 10)
            worker_pid = int(response["pid"])
            current.update(
                {
                    "phase": "recording",
                    "owner_pid": worker_pid,
                    "owner_start_ticks": core.process_start_ticks(worker_pid),
                    "recording_started_at": response.get("started_at", time.time()),
                }
            )
            core.write_state(current)
    except Exception:
        with core.ControlLock():
            current = core.read_state()
            if current and current.get("session_id") == session_id:
                core.STATE_FILE.unlink(missing_ok=True)
        raise

    core.LOG.info("Moonshine recording started: session=%s", session_id)
    core.notify(config, "Dictation: recording", "Streaming locally; release to paste")
    return 0


def finish_session(config: dict, no_paste: bool = False) -> int:
    release_started = time.monotonic()
    with core.ControlLock():
        state = core.read_state()
        if not state:
            core.LOG.info("Ignoring Moonshine stop; no session is active")
            return 0
        if state.get("instance") != "moonshine":
            core.LOG.info(
                "Ignoring Moonshine stop; session belongs to %s", state.get("instance")
            )
            return 0
        if state.get("phase") == "starting":
            state["phase"] = "stop_requested"
            core.write_state(state)
            core.LOG.info("Moonshine stop requested while worker was warming")
            return 0
        if state.get("phase") != "recording":
            core.LOG.info(
                "Ignoring duplicate Moonshine stop; phase=%s", state.get("phase")
            )
            return 0
        state["phase"] = "transcribing"
        state["owner_pid"] = os.getpid()
        state["owner_start_ticks"] = core.process_start_ticks(os.getpid())
        core.write_state(state)

    try:
        core.notify(
            config, "Dictation: finalizing", "Finishing the last streaming phrase"
        )
        response = worker_rpc(config, {"command": "stop"})
        text = str(response.get("text", "")).strip()
        recording_seconds = float(response.get("recording_seconds", 0))
        if not text:
            minimum = float(config["recording"].get("minimum_seconds", 0.25))
            if recording_seconds < minimum:
                core.LOG.info(
                    "Ignoring short Moonshine recording: %.2fs (minimum %.2fs)",
                    recording_seconds,
                    minimum,
                )
                core.notify(config, "Dictation canceled", "Recording was too short")
                return 0
            raise RuntimeError("Moonshine returned an empty transcription")
        if no_paste:
            print(text)
            pasted = False
        else:
            pasted = core.copy_and_paste(config, text, state.get("target_window"))
        metrics = core.transcription_metrics(
            text,
            recording_seconds,
            time.monotonic() - release_started,
        )
        core.LOG.info(
            "Dictation metrics: instance=moonshine model=%s recording_seconds=%.2f "
            "release_to_result_seconds=%.2f finalization_seconds=%.2f lines=%s "
            "max_line_latency_ms=%s words=%s words_per_minute=%s pasted=%s",
            config["moonshine"]["model_arch"],
            metrics["recording_seconds"],
            metrics["result_seconds"],
            float(response.get("finalization_seconds", 0)),
            response.get("lines", 0),
            response.get("max_line_latency_ms", 0),
            metrics["words"],
            metrics["words_per_minute"],
            pasted,
        )
        if no_paste:
            core.notify(
                config,
                "Dictation complete",
                core.format_completion_metrics(metrics, "Ready"),
            )
        elif pasted:
            core.notify(
                config,
                "Dictation pasted",
                core.format_completion_metrics(metrics, "Pasted"),
            )
        else:
            core.notify(
                config,
                "Dictation copied",
                core.format_completion_metrics(metrics, "Copied")
                + "; automatic paste failed—press Ctrl+Shift+V",
                urgency="critical",
            )
        return 0
    finally:
        with core.ControlLock():
            current = core.read_state()
            if current and current.get("session_id") == state.get("session_id"):
                core.STATE_FILE.unlink(missing_ok=True)


def cancel_session(config: dict) -> int:
    with core.ControlLock():
        state = core.read_state()
        if not state:
            print("idle")
            return 0
        if state.get("instance") != "moonshine":
            raise RuntimeError(f"Active session belongs to {state.get('instance')}")
        if state.get("phase") in ("starting", "stop_requested"):
            core.STATE_FILE.unlink(missing_ok=True)
            print("canceled")
            return 0
        if state.get("phase") != "recording":
            raise RuntimeError(f"Cannot cancel while session is {state.get('phase')}")
        state["phase"] = "canceling"
        state["owner_pid"] = os.getpid()
        state["owner_start_ticks"] = core.process_start_ticks(os.getpid())
        core.write_state(state)
    try:
        worker_rpc(config, {"command": "cancel"})
        core.LOG.info(
            "Moonshine recording canceled: session=%s", state.get("session_id")
        )
        core.notify(config, "Dictation canceled", "Streaming transcript discarded")
        print("canceled")
        return 0
    finally:
        with core.ControlLock():
            current = core.read_state()
            if current and current.get("session_id") == state.get("session_id"):
                core.STATE_FILE.unlink(missing_ok=True)


def status() -> int:
    with core.ControlLock():
        state = core.read_state()
        if not state:
            print("idle")
            return 1
        owner = int(state.get("owner_pid", 0))
        if core.process_matches(owner, state.get("owner_start_ticks")):
            print(
                f"{state.get('phase', 'unknown')} "
                f"(instance {state.get('instance')}, session {state.get('session_id')}, pid {owner})"
            )
            return 0
        print("stale")
        return 2


def doctor(config: dict) -> int:
    failed = False
    for command in ("xclip", "xdotool", "rotatelogs", "notify-send"):
        path = core.shutil.which(command)
        print(f"{command}: {path or 'MISSING'}")
        failed |= path is None
    display = os.environ.get("DISPLAY")
    print(f"DISPLAY: {display or 'UNSET'}")
    failed |= not bool(display)
    print(f"config: {os.environ.get('PTT_CONFIG', core.DEFAULT_CONFIG)}")
    print("profile: moonshine")
    print(f"runtime: {core.RUNTIME_HOME}")
    print(f"controller log: {core.LOG_FILE}")
    try:
        import moonshine_voice

        print(f"moonshine-voice: {moonshine_voice.__version__}")
        print(f"Moonshine model: {config['moonshine']['model_arch']}")
        try:
            probe = core.run_quiet(
                [
                    sys.executable,
                    "-c",
                    "import sounddevice as sd; print(sd.query_devices(kind='input')['name'])",
                ],
                timeout=3,
            )
            if probe.returncode:
                print(f"default input: unavailable ({probe.stderr.strip()})")
                failed = True
            else:
                print(f"default input: {probe.stdout.strip()}")
        except subprocess.TimeoutExpired:
            print("default input: probe timed out after 3 seconds")
            failed = True
    except ImportError as exc:
        print(f"Moonshine dependency missing: {exc}")
        failed = True
    print(f"Moonshine worker log: {WORKER_LOG_FILE}")
    return int(failed)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("start", help="start streaming from the default microphone")
    stop_parser = subparsers.add_parser("stop", help="finalize and paste")
    stop_parser.add_argument("--no-paste", action="store_true")
    subparsers.add_parser("cancel", help="stop and discard the active transcript")
    subparsers.add_parser("status", help="show the global dictation session")
    subparsers.add_parser("doctor", help="check Moonshine and desktop dependencies")
    subparsers.add_parser("worker-start", help="load the resident Moonshine model")
    subparsers.add_parser("worker-status", help="show the Moonshine worker")
    subparsers.add_parser("worker-stop", help="release the resident Moonshine model")
    return parser


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "_worker":
        return run_worker(core.load_config())
    args = build_parser().parse_args()
    config = core.load_config()
    if args.command == "start":
        return start_recording(config)
    if args.command == "stop":
        return finish_session(config, args.no_paste)
    if args.command == "cancel":
        return cancel_session(config)
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
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        core.LOG.warning("Moonshine command interrupted")
        raise SystemExit(130)
    except Exception as exc:
        core.LOG.exception("Moonshine command failed")
        try:
            core.notify(
                core.load_config(), "Dictation failed", str(exc), urgency="critical"
            )
        except Exception:
            pass
        print(f"ptt-dictation-moonshine: {exc}\nSee {core.LOG_FILE}", file=sys.stderr)
        raise SystemExit(1)
