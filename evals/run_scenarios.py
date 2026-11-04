"""Evaluate native replay against real local services and actual business data.

Run with ``python3 evals/run_scenarios.py --output-dir NEW-DIR``. These are
transport/account integration scenarios, not WeChat runtime or model scores.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from replay_fixture import BINARY, CASES, FORM, MULTIPART, QUERY, ReplayFixture


REPO = Path(__file__).resolve().parents[1]
REPLAY = REPO / "skills/miniapp-dynamic/scripts/replay.py"


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(case, fixture, returncode, replay_dir):
    """Derive observations first, then compare them with scenario requirements."""
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    run_path = replay_dir / "replay-run.json"
    run = _read_json(run_path) if run_path.exists() else {"results": []}
    results = {result["id"]: result for result in run["results"]}
    evidence_path = replay_dir / "evidence.json"
    evidence = _read_json(evidence_path) if evidence_path.exists() else []
    evidence_by_id = {item["evidence_id"]: item for item in evidence}
    artifacts = {}
    payloads = {}
    for identifier, result in results.items():
        refs = result.get("evidence_refs", [])
        if result.get("outcome") == "not_attempted":
            require(not refs, identifier + ": not-attempted request has fabricated wire evidence")
            continue
        require(bool(refs), identifier + ": actual attempt lacks evidence")
        for reference in refs:
            item = evidence_by_id.get(reference)
            require(item is not None, identifier + ": evidence reference does not resolve")
            if item is None:
                continue
            artifact_path = replay_dir / item["artifact"]["file"]
            require(artifact_path.is_file(), identifier + ": missing actual artifact")
            if not artifact_path.is_file():
                continue
            content = artifact_path.read_bytes()
            require(hashlib.sha256(content).hexdigest() == item["artifact"].get("hash"),
                    identifier + ": artifact digest mismatch")
            artifact = json.loads(content)
            artifacts[identifier] = artifact
            body = artifact.get("response", {}).get("body_text")
            if body is not None:
                try:
                    payloads[identifier] = json.loads(body)
                except (ValueError, TypeError):
                    pass
    observations = fixture.received
    classification = "inconclusive"
    observed = {"received_count": len(observations), "proxy_count": len(fixture.proxy_received)}

    def response(identifier, status=200):
        result = results.get(identifier, {})
        return (result.get("outcome") == "response" and result.get("response_status") == status
                and result.get("checks_passed") is True)

    def no_send(identifier):
        result = results.get(identifier, {})
        return result.get("outcome") == "not_attempted" and not result.get("evidence_refs")

    if case != "request_limit":
        require("EV-001" in evidence_by_id, "valid plan lacks real source artifact")
        require((replay_dir / "dynamic-test-results.json").is_file(), "missing request ledger")
        findings_path = replay_dir / "findings.json"
        require(findings_path.is_file() and _read_json(findings_path) == [],
                "native replay must leave vulnerability classification to the analyst")

    if case.startswith("ownership_"):
        baseline_a = payloads.get("baseline_a", {})
        baseline_b = payloads.get("baseline_b", {})
        probe = payloads.get("probe", {})
        baseline_valid = (baseline_a.get("owner") == "A" and baseline_a.get("record") == "A-record"
                          and baseline_a.get("authenticated_actor") == "A"
                          and baseline_b.get("owner") == "B" and baseline_b.get("record") == "B-record"
                          and baseline_b.get("authenticated_actor") == "B")
        require(baseline_valid, "independent A/B business baselines were not established")
        require(len(observations) == 3 and [item["actor"] for item in observations] == ["A", "B", "A"],
                "backend did not observe the A/B/A request sequence")
        if baseline_valid and probe.get("owner") == baseline_b.get("owner") and (
                probe.get("record") == baseline_b.get("record") and probe.get("authenticated_actor") == "A"):
            classification = "cross_account_data_returned"
        elif baseline_valid and response("probe", 403) and probe.get("code") == "OWNER_DENIED":
            classification = "ownership_enforced"
        observed.update(baseline_owners=[baseline_a.get("owner"), baseline_b.get("owner")],
                        probe_owner=probe.get("owner"), probe_actor=probe.get("authenticated_actor"),
                        probe_code=probe.get("code"))
        required = "cross_account_data_returned" if case == "ownership_vulnerable" else "ownership_enforced"
        require(classification == required, "business ownership result differs from local target behavior")
        require(returncode == 0 and all(response(key, 403 if key == "probe" and
                classification == "ownership_enforced" else 200) for key in ("baseline_a", "baseline_b", "probe")),
                "ownership requests did not complete their protocol expectations")
    elif case == "expired_session":
        require(returncode == 3, "expired session must make native run blocked")
        require(results.get("expired", {}).get("response_status") == 401 and no_send("blocked_a"),
                "expired actor was not stopped after actual 401")
        require(response("independent_b") and payloads.get("independent_b", {}).get("owner") == "B",
                "independent actor B did not continue")
        require([item["path"] for item in observations] == ["/expired", "/records"] and
                [item["actor"] for item in observations] == ["A", "B"],
                "upstream observed a request from the expired actor after rejection")
        classification = "expired_actor_blocked" if not failures else "inconclusive"
    elif case == "signature_required":
        require(returncode == 0 and response("unsigned", 403) and response("independent"),
                "expected signature refusal must not expire the actor")
        require(payloads.get("unsigned", {}).get("code") == "SIGNATURE_REQUIRED" and
                payloads.get("independent", {}).get("owner") == "A",
                "signature denial/accepted business response was not observed")
        require([item["signature_valid"] for item in observations] == [False, True],
                "server did not verify rejection then valid fresh signature")
        classification = "signature_required_then_verified" if not failures else "inconclusive"
    elif case == "signature_missing_adapter":
        require(returncode == 3 and len(observations) == 1 and
                observations[0]["signature_valid"] is False and
                results.get("unsigned", {}).get("outcome") == "response" and
                results.get("unsigned", {}).get("response_status") == 403 and
                results.get("unsigned", {}).get("checks_passed") is False and
                payloads.get("unsigned", {}).get("code") == "SIGNATURE_REQUIRED",
                "missing signature adapter was not blocked by the actual upstream verifier")
        classification = "signature_adapter_blocked" if not failures else "inconclusive"
    elif case == "missing_signature_key":
        require(returncode == 3 and no_send("blocked_signature") and not observations,
                "missing signing key must block before network transmission")
        classification = "signature_adapter_blocked" if not failures else "inconclusive"
    elif case in {"signed_mutation", "aes_roundtrip"}:
        require(returncode == 0 and response("baseline") and response("mutation"),
                "freshly signed baseline/mutation did not complete")
        require(len(observations) == 2 and all(item["signature_valid"] is True for item in observations),
                "server did not verify both final wire signatures")
        require(len({item.get("nonce") for item in observations}) == 2 and
                all(item.get("nonce") != "stale" for item in observations),
                "nonce was reused or captured stale derived header survived")
        require(payloads.get("baseline", {}).get("record") == "A-record" and
                payloads.get("mutation", {}).get("record") == "A-second" and
                all(payloads.get(key, {}).get("owner") == "A" for key in ("baseline", "mutation")),
                "actual business responses did not reflect the single-variable mutation")
        decoded = [json.loads(item.get("decoded_body", item["body"])) for item in observations]
        require(decoded == [{"record": "A-record"}, {"record": "A-second"}],
                "server received unexpected mutation bodies")
        for identifier, item in zip(("baseline", "mutation"), observations):
            request_artifact = artifacts.get(identifier, {}).get("request", {})
            require(request_artifact.get("body_sha256") == item["body_sha256"],
                    identifier + ": artifact is not the actual final wire-body digest")
        if case == "aes_roundtrip":
            require(all(item["encrypted"] and item["body"] != item["decoded_body"] for item in observations),
                    "server did not decrypt actual AES-GCM request envelopes")
            require(all(artifacts.get(key, {}).get("response", {}).get("decoded") is True
                        and artifacts.get(key, {}).get("response", {}).get("wire_body_sha256")
                        for key in ("baseline", "mutation")),
                    "response evidence did not distinguish decoded business data from wire ciphertext")
        classification = ("encrypted_roundtrip_verified" if case == "aes_roundtrip" else
                          "signed_mutation_verified") if not failures else "inconclusive"
    elif case == "duplicate_pairs":
        require(returncode == 0 and response("pairs") and payloads.get("pairs", {}).get("accepted") is True,
                "backend rejected repeated form/query/header preservation")
        require(len(observations) == 1 and observations[0]["body"] == FORM and
                observations[0]["target"] == "/pairs?" + QUERY and
                observations[0]["application_headers"] == ["first", "second"],
                "actual upstream pairs, encoding or duplicate headers changed")
        classification = "duplicate_pairs_preserved" if not failures else "inconclusive"
    elif case == "multipart":
        require(returncode == 0 and response("multipart") and
                payloads.get("multipart", {}).get("accepted") is True and
                len(observations) == 1 and observations[0]["body"] == MULTIPART,
                "raw binary multipart bytes/boundary were not preserved upstream")
        classification = "multipart_preserved" if not failures else "inconclusive"
    elif case == "cookie_isolation":
        require(returncode == 0 and all(response(key) for key in ("seed_a", "seed_b", "check_a", "check_b")),
                "cookie session sequence did not complete")
        require([item["actor"] for item in observations] == ["A", "B", "A", "B"] and
                [item["cookie_actor"] for item in observations] == ["A", "B", "A", "B"] and
                [item["cookie_rotated"] for item in observations] == [False, False, True, True],
                "account cookies leaked or actual Set-Cookie rotation was ignored")
        require([payloads.get(key, {}).get("owner") for key in ("seed_a", "seed_b", "check_a", "check_b")]
                == ["A", "B", "A", "B"], "actual response account markers disagree")
        classification = "isolated_cookie_sessions" if not failures else "inconclusive"
    elif case in {"proxy_http", "proxy_https", "tls_verified"}:
        require(returncode == 0 and response("baseline") and payloads.get("baseline", {}).get("owner") == "A"
                and len(observations) == 1, "verified transport did not reach the real backend")
        if case.startswith("proxy_"):
            require(len(fixture.proxy_received) == 1, "forwarding proxy did not observe the request")
            if fixture.proxy_received:
                proxy = fixture.proxy_received[0]
                require(proxy["method"] == ("CONNECT" if case == "proxy_https" else "GET"),
                        "wrong proxy protocol was used")
                require(proxy["target"] == (fixture.https_origin.removeprefix("https://") if
                        case == "proxy_https" else fixture.origin + "/records?record=A-record"),
                        "proxy saw a different upstream target")
        classification = "verified_proxy_transport" if case.startswith("proxy_") else "verified_custom_ca"
        if failures:
            classification = "inconclusive"
    elif case == "tls_untrusted":
        require(returncode == 3 and not observations and
                results.get("baseline", {}).get("outcome") == "transport_error",
                "untrusted fixture CA must fail before HTTP reaches the backend")
        error = str(results.get("baseline", {}).get("error_code", "")) + " " + str(
            results.get("baseline", {}).get("reason", ""))
        require(any(marker in error.lower() for marker in ("tls", "ssl", "certificate")),
                "TLS verification failure was not identified")
        classification = "untrusted_ca_rejected" if not failures else "inconclusive"
    elif case == "scope_refusal":
        require(returncode in (2, 3) and not observations and no_send("out_of_scope"),
                "out-of-scope target was not refused before transmission")
        classification = "scope_refused" if not failures else "inconclusive"
    elif case == "redirect":
        require(returncode == 0 and response("redirect", 302) and
                [item["path"] for item in observations] == ["/redirect"],
                "redirect was followed or original redirect response was lost")
        classification = "redirect_not_followed" if not failures else "inconclusive"
    elif case == "truncated_response":
        artifact = artifacts.get("oversized", {}).get("response", {})
        require(returncode == 3 and len(observations) == 1 and
                results.get("oversized", {}).get("checks_passed") is False and
                artifact.get("truncated") is True,
                "oversized response was not explicitly blocked and marked incomplete")
        limit = fixture.plan(case)["scope"]["max_response_bytes"]
        require(0 < artifact.get("body_bytes", 0) <= limit + 1 and
                artifact.get("body_text") is None and artifact.get("body_sha256") is None,
                "oversized response was read without a bound or presented as complete evidence")
        classification = "response_bound_enforced" if not failures else "inconclusive"
    elif case == "binary_response":
        artifact = artifacts.get("binary", {}).get("response", {})
        require(returncode == 0 and response("binary") and len(observations) == 1 and
                artifact.get("body_text") is None and artifact.get("body_bytes") == len(BINARY) and
                artifact.get("body_sha256") == hashlib.sha256(BINARY).hexdigest(),
                "binary wire response evidence was not preserved honestly")
        classification = "binary_digest_preserved" if not failures else "inconclusive"
    elif case == "missing_credentials":
        require(returncode == 3 and no_send("blocked_a") and response("independent_b") and
                payloads.get("independent_b", {}).get("owner") == "B" and
                [item["actor"] for item in observations] == ["B"],
                "missing actor credentials did not isolate the blocked account")
        classification = "missing_actor_isolated" if not failures else "inconclusive"
    elif case == "request_limit":
        require(returncode == 2 and not observations, "over-budget plan transmitted requests")
        classification = "request_budget_refused" if not failures else "inconclusive"
    else:
        raise ValueError("unknown scenario")

    if replay_dir.exists():
        for path in replay_dir.rglob("*"):
            if path.is_file():
                content = path.read_bytes()
                require(not any(secret.encode() in content for secret in fixture.environ.values()),
                        "credential value leaked into " + str(path.relative_to(replay_dir)))
    return {"case": case, "passed": not failures, "classification": classification,
            "native_exit_code": returncode, "observed": observed, "failures": failures,
            "evidence_dir": "replay", "receipt": "replay/replay-run.json" if run_path.exists() else None}


def run_case(case, output_dir):
    """Execute one real CLI subprocess, preserving independently judged evidence."""
    output_dir = Path(output_dir)
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    with ReplayFixture(vulnerable=case == "ownership_vulnerable") as fixture:
        plan_path = output_dir / "plan.json"
        _write_json(plan_path, fixture.plan(case))
        environment = {key: value for key, value in os.environ.items() if not key.startswith("FIXTURE_")}
        environment.update(fixture.environ)
        # Ambient proxy settings must not route even loopback traffic implicitly.
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            environment[name] = "http://127.0.0.1:1"
        environment["NO_PROXY"] = environment["no_proxy"] = ""
        replay_dir = output_dir / "replay"
        process = subprocess.run(
            [sys.executable, str(REPLAY), "--plan", str(plan_path), "--output-dir", str(replay_dir)],
            env=environment, capture_output=True, text=True, check=False, timeout=60,
        )
        diagnostics = {"returncode": process.returncode, "stdout": process.stdout, "stderr": process.stderr}
        for stream in ("stdout", "stderr"):
            for secret in fixture.environ.values():
                diagnostics[stream] = diagnostics[stream].replace(secret, "[REDACTED]")
        _write_json(output_dir / "process.json", diagnostics)
        _write_json(output_dir / "observed.json", {
            "received": fixture.observations(), "proxy_received": fixture.proxy_received,
        })
        result = evaluate(case, fixture, process.returncode, replay_dir)
        _write_json(output_dir / "result.json", result)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run native replay against real local service scenarios")
    parser.add_argument("--output-dir", type=Path, required=True, help="new private evidence directory")
    parser.add_argument("--case", choices=CASES, action="append", dest="cases")
    arguments = parser.parse_args(argv)
    try:
        arguments.output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    except OSError as exc:
        parser.exit(2, f"Cannot create new scenario output directory: {exc}\n")
    results = []
    for case in dict.fromkeys(arguments.cases or CASES):
        try:
            result = run_case(case, arguments.output_dir / case)
        except Exception as exc:
            # Fail visibly; never turn absent responses into a security verdict.
            result = {"case": case, "passed": False, "classification": "inconclusive",
                      "failures": [f"scenario execution failed: {type(exc).__name__}"],
                      "evidence_dir": case}
            _write_json(arguments.output_dir / case / "result.json", result)
        results.append({**result, "case_dir": case,
                        "evidence_dir": case + "/replay",
                        "receipt": case + "/" + result["receipt"] if result.get("receipt") else None})
    summary = {"version": 1, "suite": "native-loopback-integration", "results": results,
               "passed": sum(item["passed"] for item in results), "total": len(results),
               "limitations": ["Local HTTP fixtures do not evaluate WeChat runtime behavior or model quality."]}
    _write_json(arguments.output_dir / "summary.json", summary)
    print(json.dumps({"passed": summary["passed"], "total": summary["total"],
                      "summary": str(arguments.output_dir / "summary.json")}))
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
