"""Separate installed program resources from the repository being edited."""
from __future__ import annotations

import os
from pathlib import Path


def repository_root() -> Path:
    value = os.environ.get("TRITON_RISCV_REPO_ROOT") or os.environ.get("TRITON_RISCV_CHECKOUT")
    return Path(value).expanduser().resolve() if value else Path.cwd().resolve()


def state_root(repo_root: Path) -> Path:
    value = os.environ.get("TRITON_RISCV_STATE_DIR")
    return Path(value).expanduser().resolve() if value else repo_root.resolve() / "agent-results"
