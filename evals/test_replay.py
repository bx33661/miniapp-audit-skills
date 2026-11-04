"""Real CLI integration tests; run with unittest, never pytest or mocked HTTP."""

import hashlib
import http.client
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import unittest

from replay_fixture import CASES, MULTIPART, ReplayFixture
from run_scenarios import REPLAY, run_case


FIXTURE = Path(__file__).with_name("replay_fixture.py")
RUNNER = Path(__file__).with_name("run_scenarios.py")
VALIDATOR = Path(__file__).resolve().parents[1] / "scripts" / "validate_outputs.py"


class ReplayCLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def invoke(self, fixture, plan, name="native", environment=None):
        plan_path = self.root / (name + ".json")
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        target = self.root / name
        env = {key: value for key, value in os.environ.items() if not key.startswith("FIXTURE_")}
        env.update(fixture.environ)
        if environment:
            env.update(environment)
        process = subprocess.run(
            [sys.executable, str(REPLAY), "--plan", str(plan_path), "--output-dir", str(target)],
            env=env, capture_output=True, text=True, check=False, timeout=60,
        )
        return process, target

    def receipt(self, target):
        return json.loads((target / "replay-run.json").read_text(encoding="utf-8"))

    def captures(self, target):
        return [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted((target / "captures").glob("*.json"))]

    def test_native_scenarios_match_actual_business_and_server_observations(self):
        for case in CASES:
            with self.subTest(case=case):
                result = run_case(case, self.root / case)
                self.assertTrue(result["passed"], json.dumps(result, ensure_ascii=False))
                self.assertNotEqual(result["classification"], "inconclusive")
                self.assertTrue((self.root / case / "observed.json").is_file())
                if result["receipt"] is not None:
                    validation = subprocess.run(
                        [sys.executable, str(VALIDATOR), "--evidence-dir",
                         str(self.root / case / result["evidence_dir"]), "--verify-artifacts"],
                        capture_output=True, text=True, check=False, timeout=30,
                    )
                    self.assertEqual(validation.returncode, 0, validation.stderr)

    def test_wrong_hmac_key_is_real_refusal_and_not_an_ownership_verdict(self):
        with ReplayFixture() as fixture:
            plan = fixture.plan("signed_mutation")
            plan["requests"] = plan["requests"][:1]
            plan["requests"][0]["signature"]["key_env"] = "FIXTURE_WRONG_HMAC"
            process, target = self.invoke(fixture, plan, environment={"FIXTURE_WRONG_HMAC": "wrong-fixture-key"})
            self.assertEqual(process.returncode, 3, process.stderr)
            self.assertEqual(len(fixture.received), 1)
            self.assertFalse(fixture.received[0]["signature_valid"])
            result = self.receipt(target)["results"][0]
            self.assertEqual(result["response_status"], 403)
            self.assertFalse(result["checks_passed"])
            captures = [item for item in self.captures(target) if "response" in item]
            self.assertEqual(json.loads(captures[0]["response"]["body_text"])["code"], "SIGNATURE_REQUIRED")
            self.assertEqual(json.loads((target / "findings.json").read_text()), [])

    def test_wrong_response_aes_key_cannot_turn_http_200_into_success(self):
        with ReplayFixture() as fixture:
            plan = fixture.plan("aes_roundtrip")
            plan["requests"] = plan["requests"][:1]
            plan["requests"][0]["response_encryption"]["key_env"] = "FIXTURE_WRONG_AES"
            process, target = self.invoke(fixture, plan, environment={"FIXTURE_WRONG_AES": "00" * 32})
            self.assertEqual(process.returncode, 3, process.stderr)
            self.assertEqual(len(fixture.received), 1)
            self.assertTrue(fixture.received[0]["signature_valid"])
            self.assertTrue(fixture.received[0]["encrypted"])
            self.assertEqual(fixture.received[0]["status"], 200)
            result = self.receipt(target)["results"][0]
            self.assertFalse(result["checks_passed"])
            self.assertTrue(result["evidence_refs"])
            self.assertEqual(json.loads((target / "findings.json").read_text()), [])

    def test_file_body_preserves_binary_multipart_relative_to_plan(self):
        with ReplayFixture() as fixture:
            plan = fixture.plan("multipart")
            plan["requests"][0]["body"] = {"type": "file", "path": "multipart.bin"}
            (self.root / "multipart.bin").write_bytes(MULTIPART)
            process, target = self.invoke(fixture, plan)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual([record["body"] for record in fixture.received], [MULTIPART])
            request = [item["request"] for item in self.captures(target) if "request" in item][0]
            self.assertEqual(request["body_sha256"], hashlib.sha256(MULTIPART).hexdigest())
            self.assertEqual(request["body_bytes"], len(MULTIPART))

    def test_method_outside_scope_is_refused_before_send(self):
        with ReplayFixture() as fixture:
            plan = fixture.plan("multipart")
            plan["scope"]["methods"] = ["GET"]
            process, target = self.invoke(fixture, plan)
            self.assertEqual(process.returncode, 3, process.stderr)
            self.assertEqual(fixture.received, [])
            result = self.receipt(target)["results"][0]
            self.assertEqual(result["outcome"], "not_attempted")
            self.assertEqual(result["evidence_refs"], [])

    def test_origin_root_slash_matches_normalized_account_scope(self):
        with ReplayFixture() as fixture:
            plan = fixture.plan("ownership_safe")
            plan["scope"]["origins"] = [fixture.origin + "/"]
            for profile in plan["accounts"].values():
                profile["origins"] = [fixture.origin + "/"]
            process, target = self.invoke(fixture, plan)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual([record["actor"] for record in fixture.received], ["A", "B", "A"])
            self.assertEqual([record["status"] for record in fixture.received], [200, 200, 403])

    def test_existing_evidence_directory_is_never_overwritten(self):
        with ReplayFixture() as fixture:
            plan = fixture.plan("ownership_safe")
            process, target = self.invoke(fixture, plan)
            self.assertEqual(process.returncode, 0, process.stderr)
            before = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}
            observed_count = len(fixture.received)
            second, _ = self.invoke(fixture, plan)
            self.assertEqual(second.returncode, 2, second.stderr)
            self.assertEqual(len(fixture.received), observed_count)
            self.assertEqual(before, {path.relative_to(target): path.read_bytes()
                                      for path in target.rglob("*") if path.is_file()})

    def test_evidence_permissions_are_private(self):
        with ReplayFixture() as fixture:
            process, target = self.invoke(fixture, fixture.plan("binary_response"))
            self.assertEqual(process.returncode, 0, process.stderr)
            for path in [target, *target.rglob("*")]:
                with self.subTest(path=path.relative_to(target)):
                    self.assertEqual(path.stat().st_mode & 0o077, 0)

    def test_scenario_cli_writes_real_evidence_summary_and_refuses_reuse(self):
        target = self.root / "scenarios"
        command = [sys.executable, str(RUNNER), "--output-dir", str(target),
                   "--case", "ownership_safe", "--case", "ownership_vulnerable"]
        process = subprocess.run(command, capture_output=True, text=True, check=False, timeout=90)
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        summary = json.loads((target / "summary.json").read_text())
        self.assertEqual(summary["passed"], 2)
        self.assertEqual([item["classification"] for item in summary["results"]],
                         ["ownership_enforced", "cross_account_data_returned"])
        for case in ("ownership_safe", "ownership_vulnerable"):
            observations = json.loads((target / case / "observed.json").read_text())
            self.assertEqual(len(observations["received"]), 3)
            self.assertTrue((target / case / "replay/evidence.json").is_file())
        saved = (target / "summary.json").read_bytes()
        again = subprocess.run(command, capture_output=True, text=True, check=False, timeout=15)
        self.assertEqual(again.returncode, 2)
        self.assertEqual((target / "summary.json").read_bytes(), saved)

    def test_standalone_service_has_real_target_receipts_and_stops_on_sigterm(self):
        for mode in ("safe", "vulnerable", "expired"):
            with self.subTest(mode=mode):
                target = self.root / ("service-" + mode)
                process = subprocess.Popen(
                    [sys.executable, str(FIXTURE), "--serve", "--mode", mode,
                     "--output-dir", str(target)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                )
                try:
                    ready, _, _ = select.select([process.stdout], [], [], 20)
                    self.assertTrue(ready, "fixture did not emit ready manifest")
                    manifest = json.loads(process.stdout.readline())
                    self.assertTrue(manifest["ready"])
                    self.assertNotIn("mode", manifest)
                    self.assertNotIn("vulnerable", manifest)
                    from urllib.parse import urlsplit
                    origin = urlsplit(manifest["origin"])
                    connection = http.client.HTTPConnection(origin.hostname, origin.port, timeout=5)
                    try:
                        connection.request("GET", "/records?record=B-record", headers={
                            "Authorization": manifest["environ"]["FIXTURE_A_TOKEN"],
                            "Cookie": manifest["environ"]["FIXTURE_A_COOKIE"],
                        })
                        response = connection.getresponse()
                        body = json.loads(response.read())
                        self.assertEqual(response.status, {"safe": 403, "vulnerable": 200, "expired": 401}[mode])
                        if response.status == 200:
                            self.assertEqual(body["owner"], "B")
                            self.assertEqual(body["authenticated_actor"], "A")
                    finally:
                        connection.close()
                    observation = json.loads((target / "observed.json").read_text())
                    self.assertEqual(len(observation["received"]), 1)
                    self.assertEqual(observation["received"][0]["actor"], "A")
                    self.assertEqual(observation["received"][0]["target"], "/records?record=B-record")
                finally:
                    process.terminate()
                    try:
                        _, stderr = process.communicate(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate()
                        self.fail("fixture did not stop after SIGTERM")
                self.assertEqual(process.returncode, 0, stderr)


if __name__ == "__main__":
    unittest.main()
