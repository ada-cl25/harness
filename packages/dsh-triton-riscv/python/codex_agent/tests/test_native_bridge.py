from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_agent.harness.native_bridge import dispatch
from codex_agent.operator_development import prepare_operator_development, propose_operator_implementation, apply_operator_implementation, _load_proposal
from codex_agent.tests.test_operator_development import valid_spec, IMPLEMENTATION, TEST_SOURCE


class NativeBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "python/examples/flaggems").mkdir(parents=True)
        plan = prepare_operator_development(self.root, valid_spec())
        proposal = propose_operator_implementation(self.root, plan.development_id, IMPLEMENTATION, TEST_SOURCE, "fixture")
        self.request = {"kind": "development", "id": proposal.proposal_id, "session_id": "native-test"}
        self.env = patch.dict(os.environ, {"TRITON_RISCV_ALLOW_DEVELOPMENT_APPLY": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def review(self):
        return dispatch(self.root, {"action": "review", **self.request})

    def decide(self, review, outcome="allowed-once"):
        return dispatch(self.root, {"action": "decide", **self.request,
                                   "fingerprint": review["fingerprint"], "outcome": outcome})

    def test_review_is_read_only_then_exact_grant_applies(self):
        review = self.review()
        self.assertIn("test_square_new", review["reason"])
        self.assertFalse((self.root / "python/examples/flaggems/square_new.py").exists())
        self.assertEqual(apply_operator_implementation(self.root, self.request["id"]).status, "not_approved")
        self.decide(review)
        self.assertEqual(apply_operator_implementation(self.root, self.request["id"]).status, "applied")

    def test_review_change_rejects_grant(self):
        review = self.review()
        path, record = _load_proposal(self.root, self.request["id"])
        record["rationale"] = "changed"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(PermissionError, "changed"):
            self.decide(review)
        self.assertEqual(apply_operator_implementation(self.root, self.request["id"]).status, "not_approved")

    def test_rejection_cannot_apply(self):
        self.decide(self.review(), "rejected")
        self.assertEqual(apply_operator_implementation(self.root, self.request["id"]).status, "not_approved")

    def test_gate_disabled_and_unsupported_outcome_fail_closed(self):
        with patch.dict(os.environ, {"TRITON_RISCV_ALLOW_DEVELOPMENT_APPLY": "0"}):
            with self.assertRaises(PermissionError): self.review()
        with self.assertRaises(PermissionError): self.decide(self.review(), "model-said-yes")

    def test_another_session_cannot_reuse_approval(self):
        self.decide(self.review())
        self.request["session_id"] = "other"
        with self.assertRaisesRegex(PermissionError, "another"):
            self.review()

    def test_memory_delegates_to_existing_retrieval_and_excludes_current_run(self):
        with patch("codex_agent.harness.native_bridge.retrieve_operator_memory") as retrieve:
            retrieve.return_value.model_dump.return_value = {"status": "empty", "items": []}
            self.assertEqual(dispatch(self.root, {"action": "memory", "query": {"operator_name": "square", "run_id": "run-current"}})["status"], "empty")
            retrieve.assert_called_once_with(self.root, operator_name="square", run_id="run-current")
