"""Guarded SSH execution for Triton-RISCV validation."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

from pydantic import BaseModel, Field
from codex_agent.failure_diagnosis import diagnose_log

from codex_agent.validate_operator import (
    OperatorValidationResult,
    classify_log,
    extract_error_excerpt,
    slugify,
)


REMOTE_HOST_RE = re.compile(r"[A-Za-z0-9_.-]+")
REMOTE_ROOT_RE = re.compile(r"/[A-Za-z0-9_./-]+")
ALLOWED_SYNC_ROOT = PurePosixPath("python/examples/flaggems")
PREFLIGHT_TIMEOUT_SECONDS = 90
SSH_OPTIONS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]


class RemotePreflightResult(BaseModel):
    """Structured result of checking the configured RISC-V validation host."""

    configured: bool
    status: str
    host: str | None = None
    repository: str | None = None
    architecture: str | None = None
    triton_version: str | None = None
    python_path: str | None = None
    triton_shared_opt: str | None = None
    buddy_opt: str | None = None
    exit_code: int | None = None
    duration_seconds: float = 0.0
    error_excerpt: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class RemoteValidationConfig:
    """Host-owned remote target; model-facing tools cannot override it."""

    host: str
    repository: str

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "RemoteValidationConfig | None":
        env = os.environ if environ is None else environ
        host = env.get("RISCV_HOST", "").strip()
        repository = env.get("RISCV_REPO", "").strip()
        if not host and not repository:
            return None
        if not host or not repository:
            raise ValueError("RISCV_HOST and RISCV_REPO must be configured together")
        if not REMOTE_HOST_RE.fullmatch(host):
            raise ValueError("RISCV_HOST contains unsupported characters")
        if not REMOTE_ROOT_RE.fullmatch(repository):
            raise ValueError("RISCV_REPO must be an absolute path without spaces")
        normalized = PurePosixPath(repository)
        if ".." in normalized.parts:
            raise ValueError("RISCV_REPO cannot contain parent traversal")
        return cls(host=host, repository=normalized.as_posix())


def _decode_timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def _run_ssh_script(
    config: RemoteValidationConfig,
    script: str,
    arguments: list[str],
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ssh", *SSH_OPTIONS, config.host,
         shlex.join(["bash", "-s", "--", *arguments])],
        input=script,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )


PREFLIGHT_SCRIPT = r"""
set -eo pipefail
root=$1
cd "$root" || { echo "PREFLIGHT_ERROR=repository-not-found"; exit 70; }
test -f .venv/bin/activate || { echo "PREFLIGHT_ERROR=venv-not-found"; exit 71; }
test -f scripts/triton-riscv-env.sh || { echo "PREFLIGHT_ERROR=environment-script-not-found"; exit 72; }
. .venv/bin/activate
. scripts/triton-riscv-env.sh
architecture=$(uname -m)
printf 'ARCHITECTURE=%s\n' "$architecture"
test "$architecture" = riscv64 || { echo "PREFLIGHT_ERROR=not-riscv64"; exit 73; }
printf 'PYTHON_PATH=%s\n' "$(command -v python)"
version=$(python -c 'import triton; import pytest; print(triton.__version__)') || { echo "PREFLIGHT_ERROR=python-dependency-import-failed"; exit 75; }
shared=$(command -v triton-shared-opt) || { echo "PREFLIGHT_ERROR=triton-shared-opt-not-found"; exit 76; }
buddy=$(command -v buddy-opt) || { echo "PREFLIGHT_ERROR=buddy-opt-not-found"; exit 77; }
printf 'TRITON_VERSION=%s\n' "$version"
printf 'TRITON_SHARED_OPT=%s\n' "$shared"
printf 'BUDDY_OPT=%s\n' "$buddy"
command -v timeout >/dev/null || { echo "PREFLIGHT_ERROR=timeout-not-found"; exit 74; }
"""


def _fields(output: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator and key in {
            "ARCHITECTURE",
            "PYTHON_PATH",
            "TRITON_VERSION",
            "TRITON_SHARED_OPT",
            "BUDDY_OPT",
        }:
            result[key] = value.strip()
    return result


def check_remote_environment(
    config: RemoteValidationConfig | None = None,
) -> RemotePreflightResult:
    """Check architecture and required compiler tools on the configured host."""

    selected = config or RemoteValidationConfig.from_env()
    if selected is None:
        return RemotePreflightResult(
            configured=False,
            status="blocked",
            error_excerpt=["RISCV_HOST and RISCV_REPO are not configured"],
        )

    start = time.monotonic()
    try:
        completed = _run_ssh_script(
            selected,
            PREFLIGHT_SCRIPT,
            [selected.repository],
            PREFLIGHT_TIMEOUT_SECONDS,
        )
        output = completed.stdout
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        output = _decode_timeout_output(error.stdout)
        output += "\nPREFLIGHT_ERROR=ssh-timeout\n"
        exit_code = 124
    except OSError as error:
        output = f"PREFLIGHT_ERROR={error}"
        exit_code = 127
    values = _fields(output)
    required = ("PYTHON_PATH", "TRITON_VERSION", "TRITON_SHARED_OPT", "BUDDY_OPT")
    if exit_code == 0 and (values.get("ARCHITECTURE") != "riscv64" or
                           any(not values.get(key) for key in required)):
        output += "\nPREFLIGHT_ERROR=incomplete-or-invalid-environment-evidence\n"
        exit_code = 78
    status = "passed" if exit_code == 0 else "failed"
    return RemotePreflightResult(
        configured=True,
        status=status,
        host=selected.host,
        repository=selected.repository,
        architecture=values.get("ARCHITECTURE"),
        triton_version=values.get("TRITON_VERSION"),
        python_path=values.get("PYTHON_PATH"),
        triton_shared_opt=values.get("TRITON_SHARED_OPT"),
        buddy_opt=values.get("BUDDY_OPT"),
        exit_code=exit_code,
        duration_seconds=round(time.monotonic() - start, 3),
        error_excerpt=extract_error_excerpt(output) if exit_code else [],
    )


def _validated_relative_file(repo_root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError("remote validation file escaped the repository")
    if pure.parent != ALLOWED_SYNC_ROOT:
        raise ValueError("remote validation can sync only FlagGems source and tests")
    local = (repo_root.resolve() / Path(*pure.parts)).resolve()
    local.relative_to(repo_root.resolve())
    if not local.is_file():
        raise FileNotFoundError(local)
    return local


def _validated_test_nodes(operator: dict) -> list[str]:
    test_files = set(operator.get("test_files", []))
    nodes = list(operator.get("test_nodes", []))
    if not nodes:
        raise ValueError("operator has no test nodes")
    for node in nodes:
        test_file = node.split("::", 1)[0]
        if test_file not in test_files or "\n" in node or "\x00" in node:
            raise ValueError("operator contains an unsafe test node")
    return nodes


def remote_validation_command(
    operator: dict,
    config: RemoteValidationConfig,
) -> tuple[list[str], str]:
    """Build the fixed pytest argv and a reviewable remote display command."""

    command = ["python", "-m", "pytest", "-q", *_validated_test_nodes(operator), "-s"]
    display = (f"ssh {config.host} -- [isolated snapshot of {config.repository}; "
               f"fresh per-run cache] {shlex.join(command)}")
    return command, display


VALIDATION_SCRIPT = r"""
set -eo pipefail
root=$1
stage=$2
test_timeout=$3
file_count=$4
shift 4
files=()
for ((index = 0; index < file_count; index++)); do
  files+=("$1")
  shift
done
command=("$@")
case "$stage" in /tmp/triton-riscv-agent/*) ;; *) exit 79 ;; esac
test -d "$stage/payload"
: > "$stage/started"
child=""
cleanup() {
  if test -n "$child"; then
    kill -TERM "$child" 2>/dev/null || true
    wait "$child" 2>/dev/null || true
  fi
  rm -rf -- "$stage"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
cd "$root" || exit 70
. .venv/bin/activate
. scripts/triton-riscv-env.sh
work="$stage/workspace"
# Copy the small example tree, never overwrite the shared checkout or follow
# source symlinks. The installed backend/toolchain remains read-only input.
python - "$root" "$stage" "${files[@]}" <<'PY'
import os
import shutil
import sys
from pathlib import Path
root, stage = map(Path, sys.argv[1:3])
work = stage / "workspace"
budget = 100 * 1024 * 1024
copied = 0
def copy_file(src, dst):
    global copied
    src = Path(src)
    if src.is_symlink() or not src.is_file():
        raise ValueError(f"unsupported snapshot source: {src}")
    copied += src.stat().st_size
    if copied > budget:
        raise ValueError("remote source snapshot exceeds 100 MiB")
    return shutil.copy2(src, dst)
source = root / "python/examples/flaggems"
for directory, dirs, names in os.walk(source):
    dirs[:] = [name for name in dirs if name not in {"__pycache__", ".pytest_cache"}]
    if Path(directory).is_symlink() or any((Path(directory) / name).is_symlink() for name in dirs):
        raise ValueError("symlink directories are not allowed in the snapshot")
shutil.copytree(source, work / "python/examples/flaggems", copy_function=copy_file,
                ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
for relative in ("conftest.py", "pytest.ini", "pyproject.toml", "setup.cfg",
                 "python/__init__.py", "python/conftest.py",
                 "python/examples/__init__.py", "python/examples/conftest.py"):
    src = root / relative
    if src.exists():
        copy_file(src, work / relative)
for index, relative in enumerate(sys.argv[3:]):
    path = Path(relative)
    if path.parent.as_posix() != "python/examples/flaggems":
        raise ValueError("invalid snapshot destination")
    copy_file(stage / "payload" / str(index), work / path)
print(f"REMOTE_WORKSPACE={work}", flush=True)
print(f"REMOTE_SNAPSHOT_BYTES={copied}", flush=True)
PY
mkdir -p "$stage/tmp" "$stage/cache" "$stage/dump" "$stage/override"
export TMPDIR="$stage/tmp" PYTHONDONTWRITEBYTECODE=1
export TRITON_CACHE_DIR="$stage/cache" TRITON_DUMP_DIR="$stage/dump"
export TRITON_OVERRIDE_DIR="$stage/override" TRITON_SHARED_DUMP_PATH="$stage/dump/shared"
export PYTHONPATH="$work:$root:${PYTHONPATH:-}"
cd "$work"
timeout --signal=TERM --kill-after=10s "${test_timeout}s" "${command[@]}" &
child=$!
status=0
wait "$child" || status=$?
child=""
exit "$status"
"""


def _cleanup_stage(config: RemoteValidationConfig, stage: str) -> None:
    try:
        _run_ssh_script(
            config,
            'case "$1" in /tmp/triton-riscv-agent/*) '
            'test -f "$1/started" || rm -rf -- "$1" ;; esac\n',
            [stage],
            30,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def run_remote_operator(
    operator: dict,
    *,
    repo_root: Path,
    results_dir: Path,
    timeout_seconds: int,
    config: RemoteValidationConfig | None = None,
) -> tuple[OperatorValidationResult, RemotePreflightResult]:
    """Validate in a disposable source snapshot without changing the checkout."""

    selected = config or RemoteValidationConfig.from_env()
    if selected is None:
        raise ValueError("remote validation is not configured")
    preflight = check_remote_environment(selected)
    if preflight.status != "passed":
        output = "\n".join(preflight.error_excerpt)
        result = OperatorValidationResult(
            operator=operator["name"],
            implementation_file=operator["implementation_file"],
            test_files=operator["test_files"],
            command=f"ssh {selected.host} <remote-preflight>",
            dry_run=False,
            exit_code=preflight.exit_code,
            status="failed",
            failure_stage="environment",
            likely_reason="remote RISC-V environment preflight failed",
            error_excerpt=preflight.error_excerpt or [output],
            duration_seconds=preflight.duration_seconds,
            log_path=None,
        )
        return result, preflight

    relative_files = [operator["implementation_file"], *operator["test_files"]]
    relative_files = list(dict.fromkeys(relative_files))
    local_files = [
        _validated_relative_file(repo_root, relative)
        for relative in relative_files
    ]
    stage = f"/tmp/triton-riscv-agent/{uuid.uuid4().hex}"
    create = _run_ssh_script(
        selected,
        'umask 077; mkdir -p "$1/payload"\n',
        [stage],
        30,
    )
    if create.returncode != 0:
        raise RuntimeError(f"remote staging failed: {create.stdout.strip()}")

    try:
        for index, local in enumerate(local_files):
            completed = subprocess.run(
                ["scp", *SSH_OPTIONS, local.as_posix(), f"{selected.host}:{stage}/payload/{index}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"remote sync failed for {relative_files[index]}: "
                    f"{completed.stdout.strip()}"
                )

        command, display_command = remote_validation_command(operator, selected)
        arguments = [
            selected.repository,
            stage,
            str(timeout_seconds),
            str(len(relative_files)),
            *relative_files,
            *command,
        ]
        start = time.monotonic()
        try:
            completed = _run_ssh_script(
                selected,
                VALIDATION_SCRIPT,
                arguments,
                timeout_seconds + 60,
            )
            output = completed.stdout
            exit_code = completed.returncode
        except subprocess.TimeoutExpired as error:
            output = _decode_timeout_output(error.stdout)
            output += f"\nTIMEOUT after {timeout_seconds} seconds\n"
            exit_code = 124
        duration = time.monotonic() - start
    finally:
        _cleanup_stage(selected, stage)

    log_dir = results_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_path = log_dir / f"{timestamp}-{Path(stage).name[:8]}-remote-{slugify(operator['name'])}.log"
    log_path.write_text(output, encoding="utf-8")
    status, failure_stage, likely_reason = classify_log(output, exit_code)
    if exit_code == 124:
        failure_stage = "timeout"
        likely_reason = "remote validation command timed out"
    return (
        OperatorValidationResult(
            operator=operator["name"],
            implementation_file=operator["implementation_file"],
            test_files=operator["test_files"],
            command=display_command,
            dry_run=False,
            exit_code=exit_code,
            status=status,
            failure_stage=failure_stage,
            likely_reason=likely_reason,
            error_excerpt=extract_error_excerpt(output) if status == "failed" else [],
            duration_seconds=round(duration, 3),
            log_path=log_path.as_posix(),
            fresh_compile=True,
            execution_mode="native-riscv" if preflight.architecture == "riscv64" else "unknown",
            diagnosis=diagnose_log(output, exit_code, validation_command=display_command),
        ),
        preflight,
    )
