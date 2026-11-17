"""Behavior tests: no network, packages, live configuration or services touched."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("workstation_setup", Path(__file__).with_name("setup.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.root = Path(self.temp.name) / "dotfiles"
        self.root.mkdir()
        self.manifest = self.root / "bootstrap"
        self.manifest.mkdir()
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(module, "ROOT", self.root))
        self.stack.enter_context(patch.object(module, "MANIFEST", self.manifest))
        self.stack.enter_context(patch.dict(os.environ, {"HOME": str(self.home)}))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))

    def setup(self, **kwargs):
        return module.Setup(SimpleNamespace(check=False, dry_run=False, only=None, **kwargs))

    def test_conflicts_are_preserved_and_reruns_do_not_rebackup(self):
        source = self.root / "setting"
        source.write_text("new")
        dest = self.home / ".setting"
        dest.write_text("personal old settings")
        setup = self.setup()
        setup.link(source, dest)
        self.assertEqual(dest.resolve(), source)
        self.assertEqual((setup.backup / ".setting").read_text(), "personal old settings")
        setup.link(source, dest)
        self.assertEqual(len(list(setup.backup.iterdir())), 1)

    def test_check_and_dry_run_do_not_write(self):
        source = self.root / "setting"
        source.write_text("new")
        (self.manifest / "directories.json").write_text('["dev/school/uiuc/2026-fall"]')
        before = sorted(str(p) for p in self.home.rglob("*"))
        for mode in ("check", "dry_run"):
            setup = self.setup()
            setattr(setup.args, mode, True)
            setup.link(source, self.home / ".setting")
            setup.directories()
        self.assertEqual(sorted(str(p) for p in self.home.rglob("*")), before)

    def test_existing_repository_is_never_mutated(self):
        repo = self.home / "dev/course"
        (repo / ".git").mkdir(parents=True)
        (self.manifest / "repositories.json").write_text(json.dumps([
            {"path": "dev/course", "url": "example:course", "branch": "other"}
        ]))
        with patch.object(module.subprocess, "run") as run:
            self.setup().repositories()
            run.assert_not_called()

    def test_clone_keeps_branch_and_does_not_checkout_old_commit(self):
        (self.manifest / "repositories.json").write_text(json.dumps([
            {"path": "dev/course", "url": "example:course", "branch": "main", "recorded_commit": "old"}
        ]))
        with patch.object(module.subprocess, "run") as run:
            self.setup().repositories()
            self.assertEqual(run.call_count, 1)
            args = run.call_args.args[0]
            self.assertEqual(args[:5], ["git", "clone", "--recurse-submodules", "--branch", "main"])
            self.assertNotIn("old", args)

    def test_nonrepository_collision_is_reported(self):
        (self.home / "dev/course").mkdir(parents=True)
        (self.manifest / "repositories.json").write_text('[{"path":"dev/course","url":"example:course"}]')
        with self.assertRaises(RuntimeError):
            self.setup().repositories()

    def test_failure_is_nonzero_and_later_steps_still_run(self):
        setup = self.setup()
        setup.args.only = ["packages", "directories"]
        with patch.object(setup, "packages", side_effect=RuntimeError("package unavailable")), patch.object(setup, "directories") as later:
            self.assertEqual(setup.main(), 1)
            later.assert_called_once()

    def test_home_path_rejects_parent_escape(self):
        with self.assertRaises(ValueError):
            self.setup().home_path("../outside")


if __name__ == "__main__":
    unittest.main()
