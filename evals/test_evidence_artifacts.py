"""Integrity checks for retained execution artifacts and honest replay receipts."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_outputs.py"


class RetainedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="miniapp-artifacts-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / "evidence"
        (self.directory / "captures").mkdir(parents=True)
        self.artifact = self.directory / "captures" / "observed.json"
        self.artifact.write_text('{"response":{"status":403,"body_text":"forbidden"}}', encoding="utf-8")
        self.record = {
            "evidence_id": "EV-001", "source_skill": "miniapp-dynamic",
            "collected_at": "2026-11-04T00:00:00Z", "type": "dynamic_test",
            "artifact": {"file": "captures/observed.json", "hash": hashlib.sha256(self.artifact.read_bytes()).hexdigest()},
            "content_redacted": "The retained local response rejected the other test object's request with 403.",
        }
        self.write("findings.json", [])
        self.write("evidence.json", [self.record])

    def write(self, name, value):
        (self.directory / name).write_text(json.dumps(value), encoding="utf-8")

    def invoke(self):
        return subprocess.run([sys.executable, str(VALIDATOR), "--evidence-dir", str(self.directory), "--verify-artifacts"], capture_output=True, text=True, timeout=15)

    def test_retained_bytes_must_match_declared_hash(self):
        self.assertEqual(self.invoke().returncode, 0)
        self.artifact.write_text('{"response":{"status":200,"body_text":"changed"}}', encoding="utf-8")
        result = self.invoke()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("SHA256", result.stderr)

    def test_missing_and_outside_artifacts_cannot_be_verified(self):
        self.artifact.unlink()
        self.assertEqual(self.invoke().returncode, 1)
        outside = Path(self.temporary.name) / "outside.json"
        outside.write_text("not retained evidence", encoding="utf-8")
        self.record["artifact"]["file"] = "../outside.json"
        self.record["artifact"]["hash"] = hashlib.sha256(outside.read_bytes()).hexdigest()
        self.write("evidence.json", [self.record])
        result = self.invoke()
        self.assertEqual(result.returncode, 1)
        self.assertIn("inside the evidence directory", result.stderr)

    def test_no_response_cannot_claim_successful_checks(self):
        receipt = {"version": 1, "environment": "isolated local fixture", "results": [{"id": "R-001", "account": "A", "outcome": "transport_error", "response_status": None, "checks_passed": False, "evidence_refs": ["EV-001"], "reason": "Connection failed before a response."}], "limitations": []}
        self.write("replay-run.json", receipt)
        self.assertEqual(self.invoke().returncode, 0)
        receipt["results"][0]["checks_passed"] = True
        self.write("replay-run.json", receipt)
        result = self.invoke()
        self.assertEqual(result.returncode, 1)
        self.assertIn("checks_passed", result.stderr)

    def test_not_attempted_steps_cannot_invent_wire_evidence(self):
        receipt = {"version": 1, "environment": "isolated local fixture", "results": [{"id": "R-001", "account": "A", "outcome": "not_attempted", "response_status": None, "checks_passed": False, "evidence_refs": [], "reason": "A required account credential was unavailable."}], "limitations": []}
        self.write("replay-run.json", receipt)
        self.assertEqual(self.invoke().returncode, 0)
        receipt["results"][0]["evidence_refs"] = ["EV-001"]
        self.write("replay-run.json", receipt)
        self.assertEqual(self.invoke().returncode, 1)


if __name__ == "__main__":
    unittest.main()
