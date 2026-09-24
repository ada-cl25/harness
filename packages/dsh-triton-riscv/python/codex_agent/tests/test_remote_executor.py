from __future__ import annotations

import subprocess
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_agent.remote_executor import (
    RemoteValidationConfig,
    RemotePreflightResult,
    run_remote_operator,
    PREFLIGHT_SCRIPT,
    VALIDATION_SCRIPT,
    _cleanup_stage,
    _run_ssh_script,
    _validated_relative_file,
    check_remote_environment,
)


class RemoteExecutorTests(unittest.TestCase):
    def test_remote_configuration_must_be_complete_and_safe(self) -> None:
        self.assertIsNone(RemoteValidationConfig.from_env({}))
        with self.assertRaisesRegex(ValueError, "configured together"):
            RemoteValidationConfig.from_env({"RISCV_HOST": "sg2044"})
        with self.assertRaisesRegex(ValueError, "unsupported"):
            RemoteValidationConfig.from_env(
                {"RISCV_HOST": "sg2044;whoami", "RISCV_REPO": "/home/work/repo"}
            )
        config = RemoteValidationConfig.from_env(
            {"RISCV_HOST": "sg2044", "RISCV_REPO": "/home/work/triton-riscv"}
        )
        assert config is not None
        self.assertEqual(config.host, "sg2044")

    def test_sync_is_restricted_to_flaggems_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            allowed = root / "python/examples/flaggems/demo.py"
            allowed.parent.mkdir(parents=True)
            allowed.write_text("# demo\n", encoding="utf-8")

            self.assertEqual(
                _validated_relative_file(root, "python/examples/flaggems/demo.py"),
                allowed.resolve(),
            )
            with self.assertRaisesRegex(ValueError, "only FlagGems"):
                _validated_relative_file(root, "scripts/demo.py")
            with self.assertRaisesRegex(ValueError, "escaped"):
                _validated_relative_file(root, "../demo.py")

    def test_preflight_parses_required_remote_tools(self) -> None:
        config = RemoteValidationConfig("sg2044", "/home/work/triton-riscv")
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                "ARCHITECTURE=riscv64\n"
                "PYTHON_PATH=/home/work/.venv/bin/python\n"
                "TRITON_VERSION=3.4.0\n"
                "TRITON_SHARED_OPT=/home/work/.venv/bin/triton-shared-opt\n"
                "BUDDY_OPT=/home/work/buddy-mlir/build/bin/buddy-opt\n"
            ),
        )
        with patch(
            "codex_agent.remote_executor._run_ssh_script",
            return_value=completed,
        ):
            result = check_remote_environment(config)

        self.assertEqual(result.status, "passed")
        self.assertEqual(result.architecture, "riscv64")
        self.assertEqual(result.triton_version, "3.4.0")
        self.assertTrue(result.buddy_opt)

    def test_preflight_rejects_empty_tools_even_with_zero_exit(self):
        with patch("codex_agent.remote_executor._run_ssh_script", return_value=
                   subprocess.CompletedProcess([], 0, "ARCHITECTURE=riscv64\n")):
            result = check_remote_environment(RemoteValidationConfig("host", "/repo"))
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.exit_code, 78)

    def test_preflight_missing_ssh_is_structured_failure(self):
        with patch("codex_agent.remote_executor._run_ssh_script", side_effect=FileNotFoundError("ssh")):
            result = check_remote_environment(RemoteValidationConfig("host", "/repo"))
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.exit_code, 127)

    def test_ssh_arguments_are_quoted_and_noninteractive(self):
        with patch("codex_agent.remote_executor.subprocess.run") as run:
            _run_ssh_script(RemoteValidationConfig("host", "/repo"), "script", ["x;touch bad", "a b"], 1)
        argv = run.call_args.args[0]
        self.assertIn("BatchMode=yes", argv)
        self.assertEqual(argv[-1], "bash -s -- 'x;touch bad' 'a b'")

    def test_cleanup_does_not_delete_an_active_workspace(self):
        with patch("codex_agent.remote_executor._run_ssh_script") as run:
            _cleanup_stage(RemoteValidationConfig("host", "/repo"), "/tmp/triton-riscv-agent/a")
        self.assertIn('test -f "$1/started" ||', run.call_args.args[1])

    def test_result_records_fresh_cache_and_unique_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "python/examples/flaggems"
            folder.mkdir(parents=True)
            (folder / "demo.py").write_text("x = 1\n")
            (folder / "test_demo.py").write_text("def test_demo(): pass\n")
            operator = dict(name="demo", implementation_file="python/examples/flaggems/demo.py",
                            test_files=["python/examples/flaggems/test_demo.py"],
                            test_nodes=["python/examples/flaggems/test_demo.py::test_demo"])
            completed = subprocess.CompletedProcess([], 0, "1 passed in 0.1s\n")
            with patch("codex_agent.remote_executor.check_remote_environment", return_value=
                       RemotePreflightResult(configured=True, status="passed", architecture="riscv64")), \
                 patch("codex_agent.remote_executor._run_ssh_script", return_value=completed), \
                 patch("codex_agent.remote_executor.subprocess.run", return_value=completed):
                results = [run_remote_operator(operator, repo_root=root, results_dir=root / "results",
                           timeout_seconds=10, config=RemoteValidationConfig("host", "/repo"))[0]
                           for _ in range(2)]
            self.assertTrue(all(item.fresh_compile and item.status == "passed" for item in results))
            self.assertNotEqual(results[0].log_path, results[1].log_path)

    def test_preflight_import_failure_cannot_be_hidden_by_printf(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in (".venv/bin", "scripts", "fake"):
                (root / name).mkdir(parents=True)
            (root / ".venv/bin/activate").write_text("")
            (root / "scripts/triton-riscv-env.sh").write_text("")
            for name, body in {"uname": "echo riscv64", "python": "exit 1"}.items():
                executable = root / "fake" / name
                executable.write_text("#!/bin/sh\n" + body + "\n")
                executable.chmod(0o700)
            result = subprocess.run(["bash", "-s", "--", str(root)], input=PREFLIGHT_SCRIPT,
                                    capture_output=True, text=True,
                                    env={**os.environ, "PATH": f"{root}/fake:{os.environ['PATH']}"})
            self.assertEqual(result.returncode, 75)
            self.assertIn("python-dependency-import-failed", result.stdout)

    def test_real_shell_snapshot_success_failure_and_symlink_rejection(self):
        # Exercise the actual SSH payload locally; no SSH, compiler, or model.
        for mode in ("success", "failure", "symlink"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for name in (".venv/bin", "scripts", "python/examples/flaggems", "fake"):
                    (root / name).mkdir(parents=True)
                (root / ".venv/bin/activate").write_text("")
                (root / "scripts/triton-riscv-env.sh").write_text("")
                original = root / "python/examples/flaggems/demo.py"
                original.write_text("ORIGINAL\n")
                if mode == "symlink":
                    (root / "python/examples/flaggems/link.py").symlink_to(original)
                (root / "fake/python").symlink_to(sys.executable)
                timeout = root / "fake/timeout"
                timeout.write_text('#!/bin/bash\nshift 3\nexec "$@"\n')
                timeout.chmod(0o700)
                parent = Path("/tmp/triton-riscv-agent")
                parent.mkdir(exist_ok=True)
                with tempfile.TemporaryDirectory(dir=parent) as stage_name:
                    stage = Path(stage_name)
                    (stage / "payload").mkdir()
                    (stage / "payload/0").write_text("NEW\n")
                    check = ("from pathlib import Path; "
                             "assert Path('python/examples/flaggems/demo.py').read_text() == 'NEW\\n'; "
                             f"raise SystemExit({1 if mode == 'failure' else 0})")
                    result = subprocess.run(["bash", "-s", "--", str(root), stage_name, "10", "1",
                                             "python/examples/flaggems/demo.py", "python", "-c", check],
                                            input=VALIDATION_SCRIPT, text=True, capture_output=True,
                                            env={**os.environ, "PATH": f"{root}/fake:{os.environ['PATH']}"})
                    self.assertEqual(result.returncode == 0, mode == "success", result.stderr)
                    self.assertEqual(original.read_text(), "ORIGINAL\n")
                    self.assertFalse(stage.exists(), result.stderr)


if __name__ == "__main__":
    unittest.main()
