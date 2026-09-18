import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from test_metrics import PTT

spec = importlib.util.spec_from_file_location(
    "queue_test_module", Path(PTT.__file__).with_name("dictation_queue.py")
)
Q = importlib.util.module_from_spec(spec)
with mock.patch.dict("sys.modules", {"__main__": PTT}):
    spec.loader.exec_module(Q)


class QueueTests(unittest.TestCase):
    def test_worker_processes_fifo_and_failed_head_blocks_following_jobs(self):
        first, job, _ = self.make_job()
        second = self.root / "job-002.json"
        Q.save(second, dict(job, instance="small"))
        seen = []

        class EndPoll(Exception):
            pass

        def complete(command, **kwargs):
            path = Path(command[-1])
            seen.append(path.name)
            value = json.loads(path.read_text())
            value["status"] = "done"
            Q.save(path, value)
            return Q.subprocess.CompletedProcess(command, 0)

        with (
            mock.patch.object(Q.subprocess, "run", side_effect=complete),
            mock.patch.object(Q.time, "sleep", side_effect=EndPoll),
        ):
            with self.assertRaises(EndPoll):
                Q.work()
        self.assertEqual(seen, [first.name, second.name])
        Q.save(first, dict(job, status="failed"))
        Q.save(second, job)
        with (
            mock.patch.object(Q.subprocess, "run") as run,
            mock.patch.object(Q.time, "sleep", side_effect=EndPoll),
        ):
            with self.assertRaises(EndPoll):
                Q.work()
            run.assert_not_called()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.patch = mock.patch.object(Q, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.config = PTT.load_config()

    def make_job(self, status="pending"):
        audio = self.root / "recording-test.wav"
        audio.write_bytes(b"test audio")
        job = dict(
            session_id="test",
            status=status,
            audio_path=str(audio),
            config=self.config,
            created=1e12,
            target_window="123",
            instance="default",
        )
        path = self.root / "job-001.json"
        Q.save(path, job)
        return path, job, audio

    def test_stop_releases_recording_slot_without_transcribing(self):
        _, job, audio = self.make_job()
        state = dict(job, recorder_pid=999999, phase="recording")
        with (
            mock.patch.object(PTT, "safe_audio_path", return_value=audio),
            mock.patch.object(PTT, "terminate_recorder"),
            mock.patch.object(PTT, "process_matches", return_value=False),
            mock.patch.object(PTT, "read_state", return_value=state),
            mock.patch.object(PTT, "STATE_FILE", self.root / "session.json"),
            mock.patch.object(PTT, "transcribe_audio") as transcribe,
        ):
            PTT.STATE_FILE.touch()
            Q.enqueue(self.config, state)
            self.assertFalse(PTT.STATE_FILE.exists())
            self.assertTrue(audio.exists())
            transcribe.assert_not_called()
            self.assertEqual(len(Q.jobs()), 2)

    def test_transcription_failure_keeps_audio(self):
        path, _, audio = self.make_job()
        with (
            mock.patch.object(PTT, "safe_audio_path", return_value=audio),
            mock.patch.object(PTT, "wav_duration", return_value=0.1),
            mock.patch.object(
                PTT, "transcribe_audio", side_effect=RuntimeError("offline")
            ),
            mock.patch.object(Q, "notice"),
        ):
            self.assertEqual(Q.process_job(path), 1)
        self.assertTrue(audio.exists())
        self.assertEqual(json.loads(path.read_text())["status"], "failed")

    def test_tiny_clip_saved_and_text_persisted_before_paste(self):
        path, _, audio = self.make_job()

        def paste(config, text, target):
            saved = json.loads(path.read_text())
            self.assertEqual(saved["status"], "delivering")
            self.assertEqual(saved["text"], "Hello")
            self.assertEqual(text, "Hello ")
            self.assertEqual(target, "123")
            return True

        with (
            mock.patch.object(PTT, "safe_audio_path", return_value=audio),
            mock.patch.object(PTT, "wav_duration", return_value=0.1),
            mock.patch.object(PTT, "transcribe_audio", return_value=("Hello", {})),
            mock.patch.object(PTT, "copy_and_paste", side_effect=paste),
            mock.patch.object(Q, "notice"),
        ):
            self.assertEqual(Q.process_job(path), 0)
        self.assertTrue(audio.exists())
        self.assertEqual(json.loads(path.read_text())["status"], "done")

    def test_capacity_refuses_backlog_without_deleting_failed_audio(self):
        _, _, audio = self.make_job(status="failed")
        self.config["queue"] = {"max_pending": 1}
        self.assertIsNotNone(Q.capacity(self.config))
        self.assertTrue(audio.exists())

    def test_second_recording_can_start_with_pending_job(self):
        self.make_job()
        with (
            mock.patch.object(PTT, "read_state", return_value=None),
            mock.patch.object(PTT, "start_recording", return_value=0) as start,
            mock.patch.object(Q, "launch"),
        ):
            self.assertEqual(Q.control(self.config, "toggle"), 0)
            start.assert_called_once()

    def test_rapid_double_click_does_not_invert_state_twice(self):
        with (
            mock.patch.object(PTT, "read_state", return_value=None),
            mock.patch.object(PTT, "start_recording", return_value=0) as start,
            mock.patch.object(Q, "launch"),
            mock.patch.object(Q, "notice"),
        ):
            Q.control(self.config, "toggle")
            Q.control(self.config, "toggle")
            self.assertEqual(start.call_count, 1)
