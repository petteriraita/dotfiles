import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock


TEST_HOME = tempfile.TemporaryDirectory(prefix="moonshine-dictation-tests-")
os.environ["XDG_RUNTIME_DIR"] = str(Path(TEST_HOME.name) / "runtime")
os.environ["XDG_STATE_HOME"] = str(Path(TEST_HOME.name) / "state")
os.environ["PTT_INSTANCE"] = "moonshine"
os.environ["PTT_PROFILE"] = "moonshine"

MODULE_PATH = Path(__file__).resolve().parents[1] / "moonshine_dictation.py"
SPEC = importlib.util.spec_from_file_location("moonshine_dictation_test", MODULE_PATH)
MOON = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOON)


def tearDownModule():
    for handler in MOON.core.LOG.handlers:
        handler.close()
    TEST_HOME.cleanup()


class TranscriptCollectorTests(unittest.TestCase):
    def test_collects_final_lines_and_ignores_duplicate_line_ids(self):
        collector = MOON.TranscriptCollector()
        collector.on_text("mutable first guess")
        collector.on_line(
            SimpleNamespace(
                text="First final sentence.",
                line_id=10,
                last_transcription_latency_ms=420,
            )
        )
        collector.on_line(
            SimpleNamespace(
                text="First final sentence.",
                line_id=10,
                last_transcription_latency_ms=420,
            )
        )
        collector.on_line(
            SimpleNamespace(
                text="Second final sentence.",
                line_id=11,
                last_transcription_latency_ms=250,
            )
        )

        snapshot = collector.snapshot()
        self.assertEqual(
            snapshot["text"],
            "First final sentence. Second final sentence.",
        )
        self.assertEqual(snapshot["lines"], 2)
        self.assertEqual(snapshot["max_line_latency_ms"], 420)

    def test_partial_is_only_a_safety_fallback_when_no_line_completed(self):
        collector = MOON.TranscriptCollector()
        collector.on_text("unfinished phrase")

        self.assertEqual(collector.snapshot()["text"], "unfinished phrase")

        collector.on_line(
            SimpleNamespace(
                text="Finished phrase.",
                line_id=20,
                last_transcription_latency_ms=100,
            )
        )
        collector.on_text("a new mutable phrase")
        self.assertEqual(collector.snapshot()["text"], "Finished phrase.")


class ControllerRaceTests(unittest.TestCase):
    def tearDown(self):
        MOON.core.STATE_FILE.unlink(missing_ok=True)

    def test_release_while_worker_is_warming_requests_stop(self):
        MOON.core.write_state(
            {
                "session_id": "warming-session",
                "instance": "moonshine",
                "phase": "starting",
                "owner_pid": os.getpid(),
                "owner_start_ticks": MOON.core.process_start_ticks(os.getpid()),
            }
        )

        self.assertEqual(MOON.finish_session(MOON.core.load_config()), 0)
        self.assertEqual(MOON.core.read_state()["phase"], "stop_requested")

    def test_release_cannot_claim_another_backend_session(self):
        MOON.core.write_state(
            {
                "session_id": "small-session",
                "instance": "small",
                "phase": "recording",
            }
        )

        self.assertEqual(MOON.finish_session(MOON.core.load_config()), 0)
        self.assertEqual(MOON.core.read_state()["session_id"], "small-session")

    def test_complete_controller_cycle_uses_stream_result_and_cleans_state(self):
        config = MOON.core.load_config()
        worker_pid = os.getpid()

        def rpc(_config, request, response_timeout=None):
            if request["command"] == "start":
                return {"ok": True, "pid": worker_pid, "started_at": 1.0}
            if request["command"] == "stop":
                return {
                    "ok": True,
                    "text": "Streaming controller test passed.",
                    "recording_seconds": 10.0,
                    "finalization_seconds": 0.4,
                    "lines": 2,
                    "max_line_latency_ms": 300,
                }
            raise AssertionError(request)

        with (
            mock.patch.object(MOON, "ensure_worker", return_value=True),
            mock.patch.object(MOON, "worker_rpc", side_effect=rpc),
            mock.patch.object(MOON.core, "active_window_id", return_value="123"),
            mock.patch.object(MOON.core, "copy_and_paste", return_value=True) as paste,
            mock.patch.object(MOON.core, "notify"),
        ):
            self.assertEqual(MOON.start_recording(config), 0)
            self.assertEqual(MOON.core.read_state()["phase"], "recording")
            self.assertEqual(MOON.finish_session(config), 0)

        paste.assert_called_once_with(
            config,
            "Streaming controller test passed.",
            "123",
        )
        self.assertIsNone(MOON.core.read_state())


class ConfigurationTests(unittest.TestCase):
    def test_profile_selects_medium_streaming(self):
        config = MOON.core.load_config()

        self.assertEqual(config["moonshine"]["model_arch"], "medium-streaming")
        self.assertEqual(config["moonshine"]["update_interval_seconds"], 0.5)


if __name__ == "__main__":
    unittest.main()
