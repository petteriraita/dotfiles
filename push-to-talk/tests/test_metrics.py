import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


TEST_HOME = tempfile.TemporaryDirectory(prefix="ptt-dictation-tests-")
os.environ["XDG_RUNTIME_DIR"] = str(Path(TEST_HOME.name) / "runtime")
os.environ["XDG_STATE_HOME"] = str(Path(TEST_HOME.name) / "state")

MODULE_PATH = Path(__file__).resolve().parents[1] / "ptt_dictation.py"
SPEC = importlib.util.spec_from_file_location("ptt_dictation", MODULE_PATH)
PTT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PTT)


def tearDownModule():
    for handler in PTT.LOG.handlers:
        handler.close()
    TEST_HOME.cleanup()


class TranscriptionMetricsTests(unittest.TestCase):
    def test_counts_words_and_calculates_speaking_rate(self):
        metrics = PTT.transcription_metrics(
            "Okay, we're testing Whisper's output: 57 seconds.",
            recording_seconds=30.0,
            result_seconds=2.345,
        )

        self.assertEqual(metrics["words"], 7)
        self.assertEqual(metrics["words_per_minute"], 14)
        self.assertEqual(
            PTT.format_completion_metrics(metrics, "Pasted"),
            "Pasted in 2.3s after release · 30.0s recording · 7 words · 14 WPM",
        )

    def test_zero_duration_is_safe(self):
        metrics = PTT.transcription_metrics("", 0.0, 0.1)

        self.assertEqual(metrics["words"], 0)
        self.assertEqual(metrics["words_per_minute"], 0)


class RecordingFeedbackTests(unittest.TestCase):
    def test_recorder_is_advertised_as_communications_capture(self):
        command = PTT.recording_command(
            PTT.load_config(), Path("/tmp/ptt-command-test.wav")
        )

        self.assertIn("--media-category", command)
        self.assertEqual(command[command.index("--media-category") + 1], "Capture")
        self.assertIn("--media-role", command)
        self.assertEqual(command[command.index("--media-role") + 1], "Communication")

    def test_pcm_level_distinguishes_silence_and_voice_level(self):
        silence = PTT.pcm16_dbfs(b"\0\0" * 100)
        samples = PTT.array.array("h", [16384] * 100)

        self.assertLess(silence, -100)
        self.assertAlmostEqual(PTT.pcm16_dbfs(samples.tobytes()), -6.02, places=1)
        self.assertEqual(PTT.level_meter(-60), "········")
        self.assertEqual(PTT.level_meter(-12), "████████")

    def test_pipewire_graph_reports_physical_source_behind_effects(self):
        audio_path = Path("/tmp/feedback.wav")
        objects = [
            {
                "id": 10,
                "type": "PipeWire:Interface:Node",
                "info": {
                    "props": {
                        "node.name": "alsa_input.internal",
                        "node.description": "Laptop Digital Microphone",
                        "media.class": "Audio/Source",
                    }
                },
            },
            {
                "id": 20,
                "type": "PipeWire:Interface:Node",
                "info": {
                    "props": {
                        "node.name": "easyeffects_source",
                        "media.class": "Audio/Source",
                    }
                },
            },
            {
                "id": 30,
                "type": "PipeWire:Interface:Node",
                "info": {
                    "props": {
                        "node.name": "pw-record",
                        "media.filename": str(audio_path),
                    }
                },
            },
            {
                "id": 40,
                "type": "PipeWire:Interface:Link",
                "info": {"output-node-id": 10, "input-node-id": 20},
            },
            {
                "id": 41,
                "type": "PipeWire:Interface:Link",
                "info": {"output-node-id": 20, "input-node-id": 30},
            },
        ]

        self.assertEqual(
            PTT.source_from_pipewire_dump(objects, audio_path),
            "Laptop Digital Microphone",
        )

    def test_empty_transcription_is_normal_transient_notification(self):
        config = PTT.load_config()
        audio_path = PTT.RUNTIME_HOME / "recording-empty-test.wav"
        audio_path.touch()
        PTT.write_state(
            {
                "session_id": "empty-test",
                "instance": "default",
                "phase": "recording",
                "audio_path": str(audio_path),
                "recorder_pid": 999999,
            }
        )
        with (
            mock.patch.object(PTT, "stop_recording_monitor"),
            mock.patch.object(PTT, "terminate_recorder"),
            mock.patch.object(PTT, "wav_duration", return_value=10.0),
            mock.patch.object(PTT, "transcribe_audio", return_value=("", {})),
            mock.patch.object(PTT, "notify") as notify,
        ):
            self.assertEqual(PTT.finish_session(config, no_paste=True), 0)

        notify.assert_called_with(
            config,
            "Dictation: no speech detected",
            "No text was produced; check the microphone shown while recording",
            expire_ms=5000,
            transient=True,
        )
        self.assertFalse(audio_path.exists())
        self.assertIsNone(PTT.read_state())


class InstanceIsolationTests(unittest.TestCase):
    def tearDown(self):
        PTT.STATE_FILE.unlink(missing_ok=True)

    def test_optional_instance_names_do_not_replace_legacy_paths(self):
        original = PTT.INSTANCE_NAME
        try:
            PTT.INSTANCE_NAME = "default"
            self.assertEqual(PTT.instance_filename("worker.log"), "worker.log")
            PTT.INSTANCE_NAME = "small"
            self.assertEqual(PTT.instance_filename("worker.log"), "worker-small.log")
            self.assertEqual(
                PTT.instance_filename("whisper.sock"), "whisper-small.sock"
            )
        finally:
            PTT.INSTANCE_NAME = original

    def test_release_from_another_instance_cannot_claim_recording(self):
        PTT.write_state(
            {
                "session_id": "small-session",
                "instance": "small",
                "phase": "recording",
            }
        )

        self.assertEqual(PTT.finish_session({}, no_paste=True), 0)
        self.assertEqual(PTT.read_state()["session_id"], "small-session")


class BoundedComponentLogTests(unittest.TestCase):
    @unittest.skipUnless(
        PTT.shutil.which(PTT.ROTATELOGS_COMMAND), "rotatelogs unavailable"
    )
    def test_keeps_only_current_log_and_one_bounded_backup(self):
        log_path = Path(TEST_HOME.name) / "bounded.log"

        with PTT.bounded_component_log(log_path) as stream:
            stream.write(b"x" * 2_500_000)

        deadline = PTT.time.monotonic() + 2
        while PTT.time.monotonic() < deadline:
            PTT.reap_component_log_sinks()
            if not PTT._LOG_SINK_PROCESSES:
                break
            PTT.time.sleep(0.01)

        files = sorted(log_path.parent.glob("bounded.log*"))
        self.assertFalse(PTT._LOG_SINK_PROCESSES)
        self.assertEqual(
            [path.name for path in files], ["bounded.log", "bounded.log.1"]
        )
        # rotatelogs checks the threshold after each write, so the file may
        # contain one additional pipe-sized block beyond 1 MiB.
        self.assertLessEqual(max(path.stat().st_size for path in files), 1_200_000)
        self.assertLessEqual(sum(path.stat().st_size for path in files), 2_100_000)


if __name__ == "__main__":
    unittest.main()
