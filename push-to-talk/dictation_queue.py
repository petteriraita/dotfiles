"""Persistent FIFO for Whisper; capture control never waits for transcription."""

import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from contextlib import contextmanager

# Reuse the running controller, including its selected Small/Turbo profile.
core = sys.modules.get("__main__")
if not hasattr(core, "STATE_HOME"):
    import ptt_dictation as core

ROOT = core.STATE_HOME / "queue"


@contextmanager
def lock(name, blocking=True):
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (ROOT / name).open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        yield


def save(path, value):
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    with temporary.open("w") as handle:
        os.chmod(temporary, 0o600)
        json.dump(value, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def jobs():
    result = []
    for path in sorted(ROOT.glob("job-*.json")):
        try:
            result.append((path, json.loads(path.read_text())))
        except FileNotFoundError:
            continue  # Completed jobs can be pruned concurrently.
    return result


def notice(config, text):
    core.notify(config, "Dictation queue", text, expire_ms=5000, transient=True)


def prune(config):
    cutoff = time.time() - config.get("queue", {}).get("retention_hours", 24) * 3600
    for path, job in jobs():
        if job["status"] in ("done", "empty") and job["created"] < cutoff:
            core.safe_audio_path(job["audio_path"]).unlink(missing_ok=True)
            path.unlink()


def capacity(config):
    prune(config)
    settings = config.get("queue", {})
    pending = sum(job["status"] not in ("done", "empty") for _, job in jobs())
    used = 0
    for path in ROOT.iterdir():
        try:
            used += path.stat().st_size
        except FileNotFoundError:
            continue
    # Reserve enough space for one maximum-length recording before opening mic.
    reserve = int(settings.get("max_recording_seconds", 300)) * 32000 + 1024 * 1024
    if pending >= settings.get("max_pending", 10):
        return "Queue full (10 clips by default). Wait for processing or inspect queue-status."
    if used + reserve > settings.get("max_storage_mb", 100) * 1024 * 1024:
        return (
            "Saved audio storage is full. Inspect queue-status; no recording started."
        )
    return None


def launch():
    # Only the elected worker runs; redundant launchers immediately exit.
    try:
        with lock("worker.lock", blocking=False):
            pass
    except BlockingIOError:
        return
    with core.bounded_component_log(core.STATE_HOME / "queue.log") as output:
        subprocess.Popen(
            [sys.executable, str(core.PROJECT_DIR / "ptt_dictation.py"), "_queue"],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=output,
            start_new_session=True,
        )


def enqueue(config, state):
    # Finalize under the command lock. Transcription and monitor teardown do
    # not hold this lock; the next press can open a new microphone immediately.
    core.terminate_recorder(state, config["recording"].get("stop_timeout_seconds", 5))
    audio = core.safe_audio_path(state["audio_path"])
    if core.process_matches(state["recorder_pid"], state.get("recorder_start_ticks")):
        raise RuntimeError("Recorder has not stopped; keeping session and audio")
    with audio.open("rb") as handle:
        os.fsync(handle.fileno())
    job = dict(state, config=config, status="pending", created=time.time())
    job_path = ROOT / f"job-{time.time_ns():020d}-{state['session_id']}.json"
    save(job_path, job)
    with core.ControlLock():
        current = core.read_state()
        if current and current["session_id"] == state["session_id"]:
            core.STATE_FILE.unlink(missing_ok=True)
    core.LOG.info("Queued recording: %s", job_path.name)
    # The monitor observes missing/different session_id and exits by itself.


def control(config, command, expected_session=None):
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    launch()
    # Reject excessive parallel invocations instead of accumulating clicks.
    try:
        with lock("commands.lock", blocking=False):
            state = core.read_state()
            if expected_session and (
                not state or state["session_id"] != expected_session
            ):
                return 0
            if command == "toggle":
                stamp = ROOT / "last-toggle.json"
                previous = json.loads(stamp.read_text()) if stamp.exists() else 0
                now = time.monotonic()
                if 0 <= now - previous < 0.15:
                    notice(
                        config,
                        "Clicks too close together; wait a moment and press again.",
                    )
                    return 0
                save(stamp, now)
                command = "stop" if state else "start"
            if state and state.get("instance", "default") != core.INSTANCE_NAME:
                notice(
                    config,
                    "The other dictation key is recording; finish that clip first.",
                )
                return 0
            if command == "cancel":
                return core.cancel_session(config)
            if command == "start":
                if state and not core.process_matches(
                    int(state.get("owner_pid", 0)), state.get("owner_start_ticks")
                ):
                    enqueue(config, state)
                    state = None
                if not state:
                    reason = capacity(config)
                    if reason:
                        notice(config, reason)
                        return 0
                result = core.start_recording(config)
            elif command == "stop":
                if state and state.get("phase") == "recording":
                    enqueue(config, state)
                result = 0
            else:
                result = 0
    except BlockingIOError:
        notice(config, "Still handling the last press; press again in a moment.")
        return 0
    launch()
    return result


def process_job(path):
    job = json.loads(path.read_text())
    config = job["config"]
    job.update(
        process_pid=os.getpid(), process_ticks=core.process_start_ticks(os.getpid())
    )
    save(path, job)
    try:
        audio = core.safe_audio_path(job["audio_path"])
        duration = core.wav_duration(audio)
        # No minimum-duration discard: even very short audio is saved/attempted.
        text, _ = core.transcribe_audio(config, audio)
        job.update(text=text, duration=duration, status="ready")
        save(path, job)
        if not text.strip():
            job["status"] = "empty"
            save(path, job)
            notice(config, "No speech recognized; audio saved for inspection.")
            return 0
        # Persist text BEFORE touching X11. A crash after this marker must not
        # automatically paste again: X11 cannot acknowledge exactly-once paste.
        job["status"] = "delivering"
        save(path, job)
        delivered = core.copy_and_paste(config, text + " ", job.get("target_window"))
        job["status"] = "done" if delivered else "delivery-failed"
        job["finished"] = time.time()
        save(path, job)
        metrics = core.transcription_metrics(
            text, duration, time.time() - job["created"]
        )
        core.LOG.info("Queue result %s: %s", path.name, metrics)
        notice(
            config,
            core.format_completion_metrics(
                metrics, "Pasted" if delivered else "Copied"
            ),
        )
        return 0 if delivered else 1
    except Exception as exc:
        job.update(status="failed", error=str(exc))
        save(path, job)
        core.LOG.exception("Queued dictation failed: %s", path)
        notice(config, "Processing failed; audio retained. Inspect queue-status.")
        return 1


def work():
    try:
        with lock("worker.lock", blocking=False):
            save(
                ROOT / "consumer.json",
                {
                    "pid": os.getpid(),
                    "start_ticks": core.process_start_ticks(os.getpid()),
                },
            )
            while True:
                pending = [
                    (p, j) for p, j in jobs() if j["status"] not in ("done", "empty")
                ]
                if not pending:
                    time.sleep(0.5)
                    continue
                path, job = pending[0]
                if job["status"] not in ("pending", "processing", "ready"):
                    # Failed/ambiguous delivery blocks later pastes to preserve order.
                    time.sleep(0.5)
                    continue
                job["status"] = "processing"
                save(path, job)
                env = dict(
                    os.environ,
                    PTT_INSTANCE=job.get("instance", "default"),
                    PTT_PROFILE=""
                    if job.get("instance", "default") == "default"
                    else job["instance"],
                )
                try:
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(core.PROJECT_DIR / "ptt_dictation.py"),
                            "_queue-job",
                            str(path),
                        ],
                        env=env,
                        timeout=600,
                        check=False,
                    )
                    if (
                        result.returncode
                        and json.loads(path.read_text())["status"] == "processing"
                    ):
                        job.update(
                            status="failed", error="Transcription subprocess exited"
                        )
                        save(path, job)
                except subprocess.TimeoutExpired:
                    current = json.loads(path.read_text())
                    current.update(
                        status="failed",
                        error="Processing exceeded 10 minutes; inspect text before retry",
                    )
                    save(path, current)
    except BlockingIOError:
        return 0


def manage(command, job_name=None):
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if command == "queue-stop":
        if any(j["status"] in ("processing", "delivering") for _, j in jobs()):
            raise RuntimeError(
                "Wait for the current queued job to finish before stopping"
            )
        path = ROOT / "consumer.json"
        if path.exists():
            core.terminate_worker_process(json.loads(path.read_text()))
        return 0
    if job_name:
        path = (ROOT / job_name).resolve()
        if path.parent != ROOT.resolve() or not path.name.startswith("job-"):
            raise RuntimeError("Invalid job name")
        # Refuse mutation while processing rather than racing with the worker.
        with lock("commands.lock", blocking=False):
            job = json.loads(path.read_text())
            if job["status"] in ("pending", "processing", "ready") or (
                job["status"] == "delivering"
                and core.process_matches(
                    int(job.get("process_pid", 0)), job.get("process_ticks")
                )
            ):
                raise RuntimeError("Job is still queued or processing")
            job["status"] = "pending" if command == "queue-retry" else "done"
            save(path, job)
    if command in ("queue-resume", "queue-retry", "queue-skip"):
        launch()
    for path, job in jobs():
        print(f"{job['status']:16} {path.name} {job['audio_path']}")
    referenced = {job["audio_path"] for _, job in jobs()}
    for audio in ROOT.glob("recording-*.wav"):
        if str(audio) not in referenced:
            print(
                f"active/orphan    {audio} (retained; transcribe-file can recover finalized WAVs)"
            )
    print(f"Saved audio and transcription text: {ROOT}")
    return 0


def internal(arguments):
    if arguments[0] == "_queue":
        return work()
    path = Path(arguments[1]).resolve()
    if path.parent != ROOT.resolve() or not path.name.startswith("job-"):
        raise RuntimeError("Invalid queue job path")
    return process_job(path)
