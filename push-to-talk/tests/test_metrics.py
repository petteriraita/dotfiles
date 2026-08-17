import importlib.util
import os
from pathlib import Path
import tempfile
import unittest


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


class BoundedComponentLogTests(unittest.TestCase):
    @unittest.skipUnless(PTT.shutil.which(PTT.ROTATELOGS_COMMAND), "rotatelogs unavailable")
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
        self.assertEqual([path.name for path in files], ["bounded.log", "bounded.log.1"])
        # rotatelogs checks the threshold after each write, so the file may
        # contain one additional pipe-sized block beyond 1 MiB.
        self.assertLessEqual(max(path.stat().st_size for path in files), 1_200_000)
        self.assertLessEqual(sum(path.stat().st_size for path in files), 2_100_000)


if __name__ == "__main__":
    unittest.main()
