"""Trusted local Harness adapter. Never exported to the model as an MCP tool."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from codex_agent import operator_development as development
from codex_agent import operator_lifecycle as lifecycle
from codex_agent.memory_api import retrieve_operator_memory
from codex_agent.paths import repository_root
from codex_agent import project_tools


GATES = {
    "development": "TRITON_RISCV_ALLOW_DEVELOPMENT_APPLY",
    "repair": "TRITON_RISCV_ALLOW_REPAIR_APPLY",
    "validation": "TRITON_RISCV_ALLOW_VALIDATION",
    "job": "TRITON_RISCV_ALLOW_VALIDATION",
}


def _artifact(root: Path, kind: str, identifier: str) -> dict[str, Any]:
    development._safe_id(identifier, "artifact_id")
    if kind == "development":
        return development._load_proposal(root, identifier)[1]
    if kind == "repair":
        return lifecycle._load_proposal(root, identifier)[1]
    if kind == "validation":
        return lifecycle._load_receipt(root, identifier)
    if kind == "job":
        return project_tools.load_job(root, identifier)
    raise ValueError("unsupported approval kind")


def _fingerprint(record: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def review_artifact(root: Path, kind: str, identifier: str, session_id: str) -> dict[str, Any]:
    if kind not in GATES or os.environ.get(GATES[kind]) != "1":
        raise PermissionError(f"Host must explicitly enable {GATES.get(kind, 'a supported operation')}")
    record = _artifact(root, kind, identifier)
    approval = record.get("approval", {}) if kind in {"validation", "job"} else record
    status = approval.get("status", "pending_approval")
    if status == "approved":
        reviewer = approval.get("reviewer") if kind in {"validation", "job"} else record.get("review", {}).get("reviewer")
        if reviewer != f"native-harness:{session_id}":
            raise PermissionError("Artifact was approved by another host/session")
    elif status != "pending_approval":
        raise PermissionError(f"Artifact cannot be approved in state {status}")
    if kind == "validation" and (record.get("status") != "planned" or approval.get("execution_run_id")):
        raise PermissionError("Validation plan has already been consumed")
    if kind == "job":
        if record["status"] != "planned":
            raise PermissionError("Validation job has already been consumed")
        project_tools.check_job_sources(root, record)
    details = {
        "kind": kind, "id": identifier, "operator": record.get("operator"),
        "implementation_file": record.get("implementation_file"),
        "test_files": record.get("test_files") or [record.get("test_file")],
        "command": record.get("command"), "execution_target": record.get("execution_target"),
        "rationale": record.get("rationale"), "diff": record.get("diff"),
    }
    if kind == "job":
        details["items"] = [{"id": item["id"], "command": item.get("command") or item.get("plan", {}).get("command")}
                            for item in record["items"]]
        details["timeout_seconds_per_target"] = record["timeout_seconds"]
    reason = json.dumps(details, ensure_ascii=False, indent=2)
    if len(reason.encode()) > 120_000:
        raise ValueError("Proposal is too large for inline review; split it into smaller proposals")
    return {"fingerprint": _fingerprint(record), "reason": reason, "status": status}


def dispatch(root: Path, request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    if action == "memory":
        result = retrieve_operator_memory(root, **request["query"])
        return result.model_dump(mode="json")
    if action not in {"review", "decide"}:
        raise ValueError("unsupported host action")
    kind, identifier, session_id = request["kind"], request["id"], request["session_id"]
    development._safe_id(session_id, "session_id")
    review = review_artifact(root, kind, identifier, session_id)
    if action == "review":
        return review
    if review["fingerprint"] != request.get("fingerprint"):
        raise PermissionError("Artifact changed during review; approval was not recorded")
    if request.get("outcome") not in {"allowed-once", "rejected"}:
        raise PermissionError("Only a settled native human approval can record a decision")
    if review["status"] == "approved":
        if request["outcome"] != "allowed-once":
            raise PermissionError("Previously approved action was not reauthorized")
        return {"status": "approved"}
    decide = {
        "development": development.decide_operator_development_proposal,
        "repair": lifecycle.decide_repair_proposal,
        "validation": lifecycle.decide_validation_plan,
        "job": project_tools.decide_validation_job,
    }[kind]
    return decide(root, identifier, approve=request["outcome"] == "allowed-once",
                  reviewer=f"native-harness:{session_id}", note="Native Harness approval service decision")


def main() -> int:
    try:
        raw = sys.stdin.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("host request exceeds limit")
        result = dispatch(repository_root(), json.loads(raw))
    except (ValueError, PermissionError, KeyError, FileNotFoundError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
