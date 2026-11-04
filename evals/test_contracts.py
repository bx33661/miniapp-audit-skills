"""Behavioral regression cases for output contracts and cross-record evidence."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_outputs.py"


def evidence() -> dict:
    return {
        "evidence_id": "EV-001",
        "source_skill": "miniapp-dynamic",
        "collected_at": "2026-11-04T00:00:00Z",
        "type": "dynamic_test",
        "artifact": {"file": "captures/synthetic.http"},
        "content_redacted": "Synthetic fixture: account A requests test order B; response contains order B.",
    }


def confirmed() -> dict:
    return {
        "finding_id": "F-021",
        "status": "confirmed",
        "title": "Synthetic order ownership fixture",
        "category": "security",
        "asset": "GET /orders/test-order-b",
        "evidence_level": "E2",
        "severity": "MEDIUM",
        "severity_reason": "Fixture demonstrates one authorized test object's exposure, without a broader scope claim.",
        "evidence_refs": ["EV-001"],
        "preconditions": "Two authorized fixture accounts and their test orders.",
        "root_cause": "The fixture does not bind the requested order to the authenticated owner.",
        "reproduction": "Compare A reading A's order with A requesting B's test order.",
        "impact": "The fixture returns the other test account's order.",
        "remediation": ["Enforce ownership at the server-side order read."],
        "verification": {
            "method": "dynamic_test",
            "test_case": {
                "expected": "A cannot read B's order.",
                "actual": "The synthetic response includes B's test order.",
            },
        },
        "retest": "Not run: repeat the two-account comparison; A's own order works and B's is denied.",
    }


def pending() -> dict:
    return {
        "finding_id": "F-021",
        "status": "needs_validation",
        "title": "Order ownership needs a second account",
        "category": "security",
        "asset": "GET /orders/{id}",
        "evidence_level": "E1",
        "priority": "P1",
        "evidence_refs": ["EV-001"],
        "validation_needed": "Obtain an authorized second account and compare test order access.",
    }


def experiment(status: str = "CONFIRMED") -> dict:
    record = {
        "finding_id": "F-021",
        "test_type": "horizontal_privilege_escalation",
        "asset": "GET /orders/test-order-b",
        "identity": "test-account-a",
        "status": status,
        "expected": "Deny another account's test order.",
        "actual": "Synthetic order B response.",
        "evidence_refs": ["EV-001"],
    }
    if status in ("CONFIRMED", "FALSE_POSITIVE"):
        record.update({
            "baseline": {"request": "GET /orders/test-order-a as A", "response": "Order A fixture response"},
            "mutation": "Replace only the test order ID.",
            "reproduction": ["Replay the normal test order read, then the ID mutation."],
        })
    if status == "CONFIRMED":
        record["evidence_level"] = "E2"
    else:
        record["reason"] = "The fixture requires additional controlled evidence."
    return {
        "skill": "miniapp-dynamic",
        "tested_at": "2026-11-04T00:00:00Z",
        "environment": "https://fixture.example.invalid",
        "entry_mode": "hypothesis",
        "requests": [],
        "findings": [record],
        "limitations": [],
    }


class OutputContractTests(unittest.TestCase):
    def run_bundle(self, findings: list, records: list | None = None, **artifacts: dict) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(prefix="miniapp-contract-") as temporary:
            directory = Path(temporary)
            payloads = {"findings.json": findings, "evidence.json": [evidence()] if records is None else records}
            payloads.update(artifacts)
            for filename, payload in payloads.items():
                (directory / filename).write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run([sys.executable, str(VALIDATOR), "--evidence-dir", str(directory)], capture_output=True, text=True, timeout=15)

    def assert_valid(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_invalid(self, result: subprocess.CompletedProcess, error_fragment: str) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(error_fragment, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_confirmed_black_box_record_needs_no_fabricated_source_line(self):
        self.assert_valid(self.run_bundle([confirmed()]))
        record = confirmed()
        del record["asset"]
        self.assert_invalid(self.run_bundle([record]), "asset")

    def test_pattern_or_static_hypothesis_cannot_be_confirmed(self):
        for level in ("E0", "E1"):
            with self.subTest(level=level):
                record = confirmed()
                record["evidence_level"] = level
                self.assert_invalid(self.run_bundle([record]), "evidence_level")

    def test_confirmed_requires_observed_result_and_reproduction(self):
        for field in ("reproduction", "severity_reason", "root_cause", "retest"):
            with self.subTest(field=field):
                record = confirmed()
                del record[field]
                self.assert_invalid(self.run_bundle([record]), field)
        record = confirmed()
        del record["verification"]["test_case"]["actual"]
        self.assert_invalid(self.run_bundle([record]), "actual")

    def test_candidates_have_priority_without_final_severity(self):
        self.assert_valid(self.run_bundle([pending()]))
        record = pending()
        record["severity"] = "CRITICAL"
        self.assert_invalid(self.run_bundle([record]), "severity")

    def test_rejected_claim_requires_a_reason_and_has_no_severity(self):
        record = pending()
        record.update(status="rejected", rejection_reason="The controlled fixture enforces ownership.")
        del record["validation_needed"]
        self.assert_valid(self.run_bundle([record]))
        del record["rejection_reason"]
        self.assert_invalid(self.run_bundle([record]), "rejection_reason")

    def test_empty_evidence_and_dangling_references_are_rejected(self):
        for excerpt in ("", " \n\t"):
            with self.subTest(excerpt=excerpt):
                record = evidence()
                record["content_redacted"] = excerpt
                self.assert_invalid(self.run_bundle([confirmed()], [record]), "content_redacted")
        self.assert_invalid(self.run_bundle([confirmed()], []), "unknown evidence ID EV-001")
        record = confirmed()
        record["evidence_refs"] = []
        self.assert_invalid(self.run_bundle([record]), "evidence_refs")

    def test_ids_remain_stable_and_unique(self):
        self.assert_invalid(self.run_bundle([confirmed(), copy.deepcopy(confirmed())]), "duplicate ID F-021")
        self.assert_invalid(self.run_bundle([confirmed()], [evidence(), copy.deepcopy(evidence())]), "duplicate ID EV-001")
        record = confirmed()
        record["status"] = "verified"
        self.assert_invalid(self.run_bundle([record]), "status")

    def test_inconclusive_and_blocked_are_valid_distinct_outcomes(self):
        for state in ("INCONCLUSIVE", "BLOCKED"):
            with self.subTest(state=state):
                data = experiment(state)
                self.assert_valid(self.run_bundle([pending()], **{"dynamic-test-results.json": data}))
                del data["findings"][0]["reason"]
                self.assert_invalid(self.run_bundle([pending()], **{"dynamic-test-results.json": data}), "reason")

    def test_dynamic_confirmation_requires_baseline_and_evidence(self):
        self.assert_valid(self.run_bundle([confirmed()], **{"dynamic-test-results.json": experiment()}))
        for field in ("baseline", "evidence_level", "reproduction"):
            with self.subTest(field=field):
                data = experiment()
                del data["findings"][0][field]
                self.assert_invalid(self.run_bundle([pending()], **{"dynamic-test-results.json": data}), field)
        data = experiment()
        data["findings"][0]["severity"] = "HIGH"
        self.assert_invalid(self.run_bundle([pending()], **{"dynamic-test-results.json": data}), "severity")

    def test_untriggered_payload_cannot_be_reported_as_false_positive_without_proof(self):
        data = experiment("FALSE_POSITIVE")
        data["findings"][0]["evidence_refs"] = []
        self.assert_invalid(self.run_bundle([pending()], **{"dynamic-test-results.json": data}), "evidence_refs")

    def test_domain_outputs_use_the_shared_finding_contract_offline(self):
        for filename, time_key in (("authz-findings.json", "scanned_at"), ("payment-findings.json", "scanned_at"), ("dataflow-analysis.json", "traced_at")):
            with self.subTest(filename=filename):
                data = {"skill": "miniapp-static-audit", time_key: "2026-11-04T00:00:00Z", "source_dir": "fixture", "findings": [pending()], "limitations": []}
                self.assert_valid(self.run_bundle([pending()], **{filename: data}))
                data["findings"][0]["severity"] = "HIGH"
                self.assert_invalid(self.run_bundle([pending()], **{filename: data}), "severity")

    def test_secure_and_incomplete_samples_preserve_different_coverage(self):
        session = {"session_id": "fixture-session", "created_at": "2026-11-04T00:00:00Z", "mode": "focused", "scope": {"in_scope": ["test orders"], "out_of_scope": [], "environment": "isolated fixture", "authorization": "synthetic fixture only"}, "coverage": [{"asset": "GET /orders/{id}", "test_type": "ownership", "identity": "A and B", "status": "tested", "evidence_refs": ["EV-001"]}], "limitations": []}
        self.assert_valid(self.run_bundle([], **{"audit-session.json": session}))
        row = session["coverage"][0]
        row.update(status="not_tested", evidence_refs=[], reason="Second test account unavailable", residual_risk="Ownership boundary remains unverified")
        session["limitations"] = ["Second test account unavailable"]
        self.assert_valid(self.run_bundle([pending()], **{"audit-session.json": session}))
        del row["reason"]
        self.assert_invalid(self.run_bundle([pending()], **{"audit-session.json": session}), "reason")

    def test_untested_privacy_section_does_not_claim_pass(self):
        data = {"skill": "miniapp-static-audit", "checked_at": "2026-11-04T00:00:00Z", "source_dir": "fixture", "regulations": [], "limitations": ["Runtime collection not observed"], "sections": {"data_collection": {"status": "not_tested", "issues": [], "limitations": ["Runtime collection not observed"], "reason": "No authorized running client"}}}
        self.assert_valid(self.run_bundle([], **{"privacy-compliance.json": data}))
        data["sections"]["data_collection"]["status"] = "PASS"
        self.assert_invalid(self.run_bundle([], **{"privacy-compliance.json": data}), "status")

    def test_traffic_entry_is_valid_without_source_or_static_findings(self):
        data = experiment("BLOCKED")
        data.update(entry_mode="traffic", findings=[])
        request = {"source_ref": "synthetic-capture/session/1", "action": "Open own test order", "identity": "test-account-a", "method": "GET", "url": "https://fixture.example.invalid/orders/a", "evidence_refs": ["EV-001"], "replay": {"status": "not_attempted", "evidence_refs": [], "reason": "Waiting for an authorized replay session"}}
        data["requests"] = [request]
        self.assert_valid(self.run_bundle([], **{"dynamic-test-results.json": data}))
        request["replay"] = {"status": "succeeded", "evidence_refs": []}
        self.assert_invalid(self.run_bundle([], **{"dynamic-test-results.json": data}), "evidence_refs")
        request["replay"]["evidence_refs"] = ["EV-001"]
        self.assert_valid(self.run_bundle([], **{"dynamic-test-results.json": data}))


if __name__ == "__main__":
    unittest.main()
