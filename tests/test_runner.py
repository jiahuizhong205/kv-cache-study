"""CPU-only tests: no torch, model downloads or GPU/server execution."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("runner", ROOT / "scripts/runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def args(self, *values):
        return runner.parser().parse_args(values)

    def command(self, action, experiment="E0", *values):
        args = self.args(action, "--experiment", experiment, *values)
        cfg = runner.load_config(experiment, args.cache_mode, args.kv_gib)
        return runner.command_for(args, cfg, "model-id", "/model/snapshot", Path("/results/run"))

    def test_all_configs_fit_context(self):
        for name in ("E0", "E1", "E3"):
            self.assertGreater(runner.load_config(name)["kv_bytes"], 0)

    def test_default_is_preview(self):
        self.assertFalse(self.args("server").execute)

    def test_unknown_experiment(self):
        with self.assertRaises(ValueError):
            runner.load_config("E99")

    def test_override_does_not_mutate_config(self):
        cfg = runner.load_config("E0", "on", 2)
        self.assertTrue(cfg["prefix_cache"])
        self.assertEqual(cfg["kv_bytes"], 2 * 1024**3)
        self.assertFalse(runner.load_config("E0")["prefix_cache"])

    def test_invalid_kv(self):
        with self.assertRaises(ValueError):
            runner.load_config("E0", kv_gib=100)

    def test_cache_off_explicit(self):
        self.assertIn("--no-enable-prefix-caching", self.command("server"))

    def test_cache_on_explicit(self):
        self.assertIn("--enable-prefix-caching", self.command("server", "E1"))

    def test_eager_only_smoke(self):
        self.assertIn("--enforce-eager", self.command("server"))
        self.assertNotIn("--enforce-eager", self.command("server", "E3"))

    def test_server_not_exposed(self):
        cmd = self.command("server")
        self.assertEqual(cmd[cmd.index("--host") + 1], "127.0.0.1")

    def test_random_lengths(self):
        cmd = self.command("bench", "E3")
        self.assertEqual(cmd[cmd.index("--random-input-len") + 1], "8192")

    def test_shared_prefix_args(self):
        cmd = self.command("bench", "E1")
        self.assertIn("--prefix-repetition-prefix-len", cmd)
        self.assertNotIn("--random-input-len", cmd)

    def test_detailed_results(self):
        self.assertIn("--save-detailed", self.command("bench"))

    def test_preview_never_calls_execution(self):
        for action in ("server", "bench", "collect"):
            with patch.object(runner, "validate_execution", side_effect=AssertionError("no execution")):
                with contextlib.redirect_stdout(io.StringIO()) as stream:
                    self.assertEqual(runner.main([action]), 0)
                self.assertFalse(json.loads(stream.getvalue())["execute"])

    def test_preview_creates_no_results(self):
        with patch.object(Path, "mkdir", side_effect=AssertionError("no writes")):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(["server"]), 0)

    def test_no_approval_denied(self):
        with patch.object(runner.sys, "platform", "linux"):
            with self.assertRaises(ValueError):
                runner.validate_execution(self.args("server", "--execute"), runner.load_config("E0"), "model")

    def test_unsafe_run_id_denied(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                runner.main(["server", "--run-id", "../escape"])
        self.assertEqual(error.exception.code, 2)

    def test_url_credentials_denied(self):
        with self.assertRaises(ValueError):
            runner.validate_url("http://user:secret@localhost:18000")

    def test_url_path_denied(self):
        with self.assertRaises(ValueError):
            runner.validate_url("http://localhost:18000/v1")

    def test_local_url_accepted(self):
        runner.validate_url("http://127.0.0.1:18000")

    def test_bad_duration_denied(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                runner.main(["collect", "--duration", "0"])

    def test_custom_server_port_manifest(self):
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            runner.main(["server", "--port", "19000"])
        self.assertEqual(json.loads(stream.getvalue())["base_url"], "http://127.0.0.1:19000")

    def test_cache_state_override(self):
        self.assertEqual(runner.load_config("E3", "on")["cache_state"], "not_controlled_pilot")

    def test_markdown_relative_links(self):
        import re
        documents = [ROOT / "README.md", * (ROOT / "docs").rglob("*.md")]
        for document in documents:
            for link in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" in link or link.startswith("#"):
                    continue
                target = (document.parent / link.split("#")[0]).resolve()
                self.assertTrue(target.exists(), f"Broken link in {document.name}: {link}")

    def test_unchanged_baseline_tree_accepted(self):
        lock = runner.read_json(ROOT / "configs/engine.json")
        with patch.object(runner, "git_value", side_effect=[lock["baseline_tree_sha"], ""]) as git:
            runner.validate_engine_snapshot(lock)
        self.assertEqual(git.call_args_list[1].args, (ROOT, "status", "--porcelain", "--", "engines/vllm"))

    def test_committed_engine_change_denied(self):
        lock = runner.read_json(ROOT / "configs/engine.json")
        with patch.object(runner, "git_value", return_value="0" * 40):
            with self.assertRaisesRegex(ValueError, "tree differs"):
                runner.validate_engine_snapshot(lock)

    def test_uncommitted_engine_changes_denied(self):
        lock = runner.read_json(ROOT / "configs/engine.json")
        for status in (" M engines/vllm/file.py", "M  engines/vllm/file.py", "?? engines/vllm/new.py"):
            with self.subTest(status=status):
                with patch.object(runner, "git_value", side_effect=[lock["baseline_tree_sha"], status]):
                    with self.assertRaisesRegex(ValueError, "changes"):
                        runner.validate_engine_snapshot(lock)

    def test_missing_source_tree_denied(self):
        import subprocess
        with patch.object(runner, "git_value", side_effect=subprocess.CalledProcessError(128, "git")):
            with self.assertRaises(subprocess.CalledProcessError):
                runner.validate_engine_snapshot(runner.read_json(ROOT / "configs/engine.json"))


if __name__ == "__main__":
    unittest.main()
