#!/usr/bin/env python3
"""Execute a scoped replay plan and retain private, redacted HTTP evidence.

Only HTTP/1.1, explicit HTTP forwarding/CONNECT, and the adapters documented in
replay_support are supported. Responses are never interpreted as vulnerabilities.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import sys
import time
from datetime import datetime, timezone
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from urllib.parse import quote, unquote, unquote_plus, urlsplit
from urllib.request import Request

from replay_support import (
    ReplayError, build_accounts, decode_response_body, load_plan,
    prepare_request, redact,
)


_MASK = "[REDACTED]"
_SENSITIVE = re.compile(
    r"authorization|cookie|password|passwd|secret|token|session|signature|"
    r"(^|[-_])sign($|[-_])|api[-_]?key|access[-_]?key|private[-_]?key|"
    r"phone|mobile|email|openid|unionid|idcard|passport|realname|fullname|address",
    re.IGNORECASE,
)
_LIMITATIONS = [
    "HTTP/1.1 only; redirects and retries are disabled; no HTTP/2, WebSocket, "
    "SOCKS, authenticated proxy, target script execution, or automatic content decompression.",
    "Only the documented HMAC-SHA256 canonicalization and AES-GCM envelope are supported.",
    "Socket operations and response-body reads are bounded; operating-system DNS resolution "
    "can exceed the configured socket timeout.",
    "Redaction covers configured/common credential and personal-data fields plus known "
    "secrets; it does not claim universal personal-data detection.",
    "Request body hashes describe prepared bytes; a transport failure does not establish "
    "how many request bytes reached the target.",
    "Expectation checks assess protocol observations only; findings remain empty.",
]


def _reject_constant(_value):
    raise ValueError("Non-finite JSON value")


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _private_json(path, value):
    data = _json_bytes(value)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
    return _digest(data)


def _sensitive(name, fields):
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    return bool(_SENSITIVE.search(name)) or normalized in {
        re.sub(r"[^a-z0-9]", "", field.lower()) for field in fields
    }


def _safe_pairs(text, secrets, fields):
    # Leave non-sensitive raw encodings/order/repeated pairs intact in evidence.
    result = []
    for pair in text.split("&"):
        name, separator, value = pair.partition("=")
        decoded_name = unquote_plus(name)
        clean_name = redact(decoded_name, secrets, fields)
        if clean_name != decoded_name:
            name = quote(clean_name, safe="")
        decoded_value = unquote_plus(value)
        clean_value = _MASK if _sensitive(decoded_name, fields) else redact(decoded_value, secrets, fields)
        if clean_value != decoded_value:
            value = quote(clean_value, safe="")
        result.append(name + separator + value)
    return "&".join(result)


def _safe_url(url, secrets, fields):
    prefix, separator, query = url.partition("?")
    parts = []
    for part in redact(prefix, secrets, fields).split("/"):
        decoded = unquote(part)
        clean = redact(decoded, secrets, fields)
        parts.append(quote(clean, safe=":@[]") if clean != decoded else part)
    return "/".join(parts) + (separator + _safe_pairs(query, secrets, fields) if separator else "")


def _safe_headers(headers, secrets, fields, credential_names=()):
    credentials = {name.lower() for name in credential_names}
    return [
        {"name": redact(name, secrets, fields), "value": _MASK if
         name.lower() in credentials or _sensitive(name, fields) else
         _safe_url(value, secrets, fields) if name.lower() in {"location", "content-location", "referer"} else
         redact(value, secrets, fields)}
        for name, value in headers
    ]


def _body_view(body, headers, secrets, fields, form=False):
    try:
        text = body.decode("utf-8")
    except UnicodeError:
        return None
    if any(ord(char) < 32 and char not in "\t\r\n" for char in text):
        return None
    content_type = next((value.lower() for name, value in headers if name.lower() == "content-type"), "")
    if content_type.startswith("multipart/"):
        return None
    try:
        parsed = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        media_type = content_type.split(";", 1)[0].strip()
        if media_type == "application/json" or media_type.endswith("+json"):
            return None
        if form or content_type.split(";", 1)[0].strip() == "application/x-www-form-urlencoded":
            return _safe_pairs(text, secrets, fields)
        return redact(text, secrets, fields)
    try:
        return json.dumps(redact(parsed, secrets, fields), ensure_ascii=True, allow_nan=False)
    except (ValueError, RecursionError):
        return None


def _input_view(plan, secrets, fields, accounts):
    view = copy.deepcopy(plan)
    for step in view["requests"]:
        actor = accounts[step["account"]]
        names = [name for name, _ in actor.headers]
        if step.get("signature"):
            names.append(step["signature"].get("signature_header", "X-Signature"))
        step["url"] = _safe_url(step["url"], secrets, fields)
        step["headers"] = _safe_headers(
            [(header["name"], header["value"]) for header in step.get("headers", [])],
            secrets, fields, names,
        )
        body = step.get("body", {"type": "none"})
        if body["type"] == "base64":
            try:
                raw = base64.b64decode(body["value"], validate=True)
                safe = _body_view(raw, [(item["name"], item["value"]) for item in step["headers"]], secrets, fields)
                body["value"] = base64.b64encode(safe.encode("utf-8")).decode("ascii") if safe is not None else _MASK
            except (ValueError, TypeError):
                body["value"] = _MASK
        elif body["type"] == "text":
            body["value"] = _body_view(body["value"].encode("utf-8"),
                                       [(item["name"], item["value"]) for item in step["headers"]], secrets, fields)
        elif body["type"] == "form":
            body["value"] = [[name, _MASK if _sensitive(name, fields) else value] for name, value in body["value"]]
    return redact(view, secrets, fields)


def _pointer(document, pointer):
    value = document
    if pointer == "":
        return value
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError
    for part in pointer[1:].split("/"):
        if re.search(r"~(?![01])", part):
            raise ValueError
        key = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", key):
                raise ValueError
            value = value[int(key)]
        elif isinstance(value, dict):
            value = value[key]
        else:
            raise ValueError
    return value


def _json_equal(actual, expected):
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_json_equal(actual[key], expected[key]) for key in actual)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(_json_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def _checks(expect, status, body):
    failures = []
    if status not in expect["status"]:
        failures.append("response_status_mismatch")
    if expect.get("contains"):
        try:
            text = body.decode("utf-8")
            if any(fragment not in text for fragment in expect["contains"]):
                failures.append("response_contains_mismatch")
        except UnicodeError:
            failures.append("response_text_unavailable")
    if expect.get("json"):
        try:
            document = json.loads(body, parse_constant=_reject_constant)
        except (ValueError, UnicodeError, RecursionError):
            failures.append("response_json_invalid")
        else:
            for check in expect["json"]:
                try:
                    matched = _json_equal(_pointer(document, check["pointer"]), check["equals"])
                except (ValueError, KeyError, IndexError, TypeError):
                    matched = False
                if not matched:
                    failures.append("response_json_mismatch")
                    break
    return failures


def _expired(actor, expect, status, body):
    if status in {401, 403} and status in expect["status"]:
        return False
    if status != 403 and status in actor.expired_status and status not in expect["status"]:
        return True
    if actor.expired_json:
        try:
            document = json.loads(body, parse_constant=_reject_constant)
        except (ValueError, UnicodeError, RecursionError):
            return False
        for signal in actor.expired_json:
            try:
                if _json_equal(_pointer(document, signal["pointer"]), signal["equals"]):
                    return True
            except (ValueError, KeyError, IndexError, TypeError):
                continue
    return False


def _target(url):
    parsed = urlsplit(url)
    # Preserve even a trailing empty '?' in the original request target.
    path = parsed.path or "/"
    if "?" in url:
        path += "?" + parsed.query
    return parsed, path


def _preflight(plan, step):
    url = step["url"]
    try:
        parsed, target = _target(url)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname or
                parsed.username is not None or parsed.password is not None or
                "#" in url or "\\" in url or not url.isascii() or
                any(ord(char) <= 32 or ord(char) == 127 for char in url)):
            raise ValueError
        port = parsed.port
        if port is not None and not 1 <= port <= 65535:
            raise ValueError
        if step["method"] not in plan["scope"]["methods"]:
            raise ReplayError("scope_method", "The request method is outside the permitted scope.")
        if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Z-]+", step["method"]):
            raise ValueError
        # CONNECT and protocol upgrades escape ordinary HTTP request semantics.
        if step["method"] == "CONNECT":
            raise ReplayError("unsupported_method", "CONNECT is supported only as an internal HTTPS proxy tunnel.")
    except (ValueError, TypeError):
        raise ReplayError("invalid_request_target", "The HTTP request target is invalid.") from None
    return parsed, target


def _context_and_proxy(plan, base_dir):
    scope = plan["scope"]
    ca_file = scope.get("ca_file")
    try:
        context = ssl.create_default_context(cafile=str(base_dir / ca_file) if ca_file else None)
    except (OSError, ValueError, ssl.SSLError):
        raise ReplayError("tls_configuration", "The TLS trust configuration could not be loaded.") from None
    proxy = scope.get("proxy")
    if proxy:
        try:
            parsed = urlsplit(proxy)
            if (parsed.scheme != "http" or not parsed.hostname or not parsed.port or
                    parsed.username is not None or parsed.password is not None or
                    parsed.path or "?" in proxy or "#" in proxy or "\\" in proxy or
                    not proxy.isascii() or any(ord(char) <= 32 for char in proxy) or
                    not 1 <= parsed.port <= 65535):
                raise ValueError
        except ValueError:
            raise ReplayError("proxy_configuration", "An explicit proxy must be an HTTP host and port without credentials.") from None
        return context, parsed
    return context, None


def _classify(error):
    if isinstance(error, ReplayError):
        return error.code, error.message
    if isinstance(error, ssl.SSLCertVerificationError):
        return "tls_verification_failed", "The TLS certificate or hostname could not be verified."
    if isinstance(error, ssl.SSLError):
        return "tls_error", "The verified TLS connection failed."
    if isinstance(error, (socket.timeout, TimeoutError)):
        return "timeout", "The configured network or response deadline was exceeded."
    if isinstance(error, socket.gaierror):
        return "dns_error", "The network destination could not be resolved."
    if isinstance(error, http.client.IncompleteRead):
        return "response_incomplete", "The HTTP response ended before its framing was complete."
    if isinstance(error, http.client.HTTPException):
        return "http_protocol_error", "The HTTP connection or response framing failed."
    if isinstance(error, OSError):
        return "network_error", "The network operation failed."
    if isinstance(error, (UnicodeError, ValueError)):
        return "http_encoding_error", "The HTTP request or response encoding is unsupported."
    return "unexpected_error", "An unexpected replay error prevented a complete result."


def _exchange(prepared, actor, scope, context, proxy):
    parsed, target = _target(prepared.url)
    timeout = scope["timeout_seconds"]
    limit = scope["max_response_bytes"]
    cookie_request = Request(prepared.url, method=prepared.method)
    actor.cookies.add_cookie_header(cookie_request)
    headers = list(prepared.headers)
    cookie = cookie_request.get_header("Cookie")
    if cookie:
        headers.append(("Cookie", cookie))
    # Derive all framing headers, and retain the exact application header sequence.
    headers.insert(0, ("Host", parsed.netloc))
    headers.append(("Content-Length", str(len(prepared.body))))
    headers.append(("Connection", "close"))
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    destination = proxy.hostname if proxy else parsed.hostname
    destination_port = proxy.port if proxy else port
    if parsed.scheme == "https":
        connection = http.client.HTTPSConnection(destination, destination_port, timeout=timeout, context=context)
        if proxy:
            connection.set_tunnel(parsed.hostname, port)
    else:
        connection = http.client.HTTPConnection(destination, destination_port, timeout=timeout)
    request_target = prepared.url if proxy and parsed.scheme == "http" else target
    result = {"headers": headers, "status": None, "response_headers": [], "wire_body": b"",
              "complete": False, "truncated": False, "error_code": None, "reason": None,
              "attempted": False, "sent_complete": False}
    chunks = []
    size = 0
    response = None
    deadline = time.monotonic() + timeout
    try:
        connection.putrequest(prepared.method, request_target, skip_host=True, skip_accept_encoding=True)
        for name, value in headers:
            connection.putheader(name, value)
        result["attempted"] = True
        connection.endheaders(prepared.body)
        result["sent_complete"] = True
        active_socket = connection.sock
        response = connection.getresponse()
        result["status"] = response.status
        result["response_headers"] = response.getheaders()
        for name, value in result["response_headers"]:
            if name.lower() == "set-cookie":
                parsed_cookies = SimpleCookie()
                try:
                    parsed_cookies.load(value)
                except (CookieError, ValueError):
                    pass
                for item in parsed_cookies.values():
                    if item.value and item.value not in actor.secrets:
                        actor.secrets.append(item.value)
        actor.cookies.extract_cookies(response, cookie_request)
        # Treat server-set cookie material as secrets before rendering any artifact.
        for item in actor.cookies:
            if item.value and item.value not in actor.secrets:
                actor.secrets.append(item.value)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            if active_socket is not None:
                active_socket.settimeout(remaining)
            try:
                part = response.read1(min(65536, limit + 1 - size))
            except http.client.IncompleteRead as error:
                part = error.partial[:limit + 1 - size]
                chunks.append(part)
                size += len(part)
                raise
            if not part:
                if response.length not in {None, 0}:
                    raise http.client.IncompleteRead(b"", response.length)
                result["complete"] = True
                break
            chunks.append(part)
            size += len(part)
            if size > limit:
                raise ReplayError("response_too_large", "The HTTP response exceeded the configured byte limit.")
            if response.isclosed() and response.length in {None, 0}:
                result["complete"] = True
                break
    except Exception as error:
        if not result["attempted"]:
            code, reason = _classify(error)
            raise ReplayError(code, reason) from None
        result["error_code"], result["reason"] = _classify(error)
        result["truncated"] = response is not None
    finally:
        result["wire_body"] = b"".join(chunks)
        if response is not None:
            try:
                response.close()
            except OSError:
                pass
        try:
            connection.close()
        except OSError:
            pass
    return result


def _attempt_artifact(prepared, result, secrets, fields, actor, proxy, decoded_body=None):
    wire = result["wire_body"]
    decoded = decoded_body is not None
    body = decoded_body if decoded else wire
    response = {
        "status": result["status"],
        "headers": _safe_headers(result["response_headers"], secrets, fields),
        "body_text": _body_view(body, result["response_headers"], secrets, fields) if result["complete"] else None,
        "body_sha256": _digest(body) if result["complete"] else None,
        "body_bytes": len(body), "truncated": result["truncated"], "decoded": decoded,
    }
    if prepared.config.get("response_encryption"):
        response["wire_body_sha256"] = _digest(wire) if result["complete"] else None
        response["wire_body_bytes"] = len(wire)
    artifact = {
        "request": {
            "method": prepared.method, "url": _safe_url(prepared.url, secrets, fields),
            "headers": _safe_headers(result["headers"], secrets, fields, [name for name, _ in actor.headers]),
            "body_text": _body_view(prepared.body, result["headers"], secrets, fields,
                                    prepared.config.get("body", {}).get("type") == "form" and not prepared.config.get("encryption")),
            "body_sha256": _digest(prepared.body), "body_bytes": len(prepared.body),
            "sent_complete": result["sent_complete"],
        },
        "response": response,
    }
    if result["error_code"]:
        artifact["transport"] = {"error_code": result["error_code"], "reason": result["reason"],
                                 "proxy": _safe_url(proxy.geturl(), secrets, fields) if proxy else None}
    return artifact


def _add_evidence(output, evidence, identifier, artifact, kind, description, environment):
    relative = f"captures/{identifier}.json"
    digest = _private_json(output / relative, artifact)
    evidence.append({
        "evidence_id": identifier, "source_skill": "miniapp-dynamic", "collected_at": _now(),
        "type": kind, "artifact": {"file": relative, "hash": digest},
        "content_redacted": description,
        "metadata": {"tool": "miniapp-replay", "environment": environment},
    })


def run(plan_path, output):
    plan = load_plan(plan_path)
    if len(plan["requests"]) > plan["scope"]["max_requests"]:
        raise ReplayError("scope_request_limit", "The plan exceeds the configured request count limit.")
    accounts = build_accounts(plan, os.environ)
    secrets = [secret for actor in accounts.values() for secret in actor.secrets]
    # Read only the named adapter variables; never enumerate or retain ambient env.
    for step in plan["requests"]:
        for adapter in ("signature", "encryption", "response_encryption"):
            config = step.get(adapter, {})
            value = os.environ.get(config.get("key_env", ""))
            if value:
                secrets.append(value)
    fields = plan.get("redact_fields", [])
    try:
        output.mkdir(mode=0o700)
        os.chmod(output, 0o700)
        (output / "captures").mkdir(mode=0o700)
        os.chmod(output / "captures", 0o700)
    except OSError:
        raise ReplayError("output_directory", "The output directory must be new and its parent must be writable.") from None
    evidence, ledger, receipts = [], [], []
    environment = redact(plan["environment"], secrets, fields)
    _add_evidence(output, evidence, "EV-001", _input_view(plan, secrets, fields, accounts), "config",
                  json.dumps({"environment": environment, "requests": [step["id"] for step in plan["requests"]]}, ensure_ascii=True), environment)
    setup_error = None
    try:
        context, proxy = _context_and_proxy(plan, plan_path.parent)
    except ReplayError as error:
        setup_error = error
        context, proxy = None, None
    for step in plan["requests"]:
        actor = accounts[step["account"]]
        receipt = {"id": redact(step["id"], secrets, fields), "account": redact(step["account"], secrets, fields),
                   "outcome": "not_attempted", "response_status": None, "checks_passed": False, "evidence_refs": []}
        replay = {"status": "blocked", "evidence_refs": []}
        entry = {"source_ref": redact(step.get("source_ref", f"plan:{step['id']}"), secrets, fields),
                 "action": redact(step["action"], secrets, fields), "identity": receipt["account"],
                 "method": step["method"], "url": _safe_url(step["url"], secrets, fields),
                 "evidence_refs": ["EV-001"], "replay": replay}
        try:
            if setup_error:
                raise setup_error
            if actor.blocked_reason:
                raise ReplayError("actor_blocked", actor.blocked_reason)
            _preflight(plan, step)
            prepared = prepare_request(step, actor, plan_path.parent, os.environ)
            secrets.extend(prepared.secrets)
            result = _exchange(prepared, actor, plan["scope"], context, proxy)
        except Exception as error:
            code, reason = _classify(error)
            receipt.update(error_code=code, reason=redact(reason, secrets, fields))
            replay["reason"] = receipt["reason"]
        else:
            secrets.extend(actor.secrets)
            receipt["response_status"] = result["status"]
            receipt["outcome"] = "response" if result["complete"] else "transport_error"
            if result["status"] is not None and _expired(actor, prepared.expect, result["status"], b""):
                actor.blocked_reason = "The actor session expired according to an unexpected authentication response."
            decoded_body = None
            if result["complete"]:
                try:
                    checked_body = decode_response_body(step, result["wire_body"], os.environ)
                    if step.get("response_encryption"):
                        decoded_body = checked_body
                    failures = _checks(prepared.expect, result["status"], checked_body)
                    expired = _expired(actor, prepared.expect, result["status"], checked_body)
                    if expired:
                        actor.blocked_reason = "The actor session expired according to an unexpected authentication response."
                        failures.append("actor_session_expired")
                    if failures:
                        receipt.update(error_code=failures[0], reason="; ".join(failures))
                    else:
                        receipt["checks_passed"] = True
                        replay["status"] = "succeeded"
                except Exception as error:
                    code, reason = _classify(error)
                    receipt.update(error_code=code, reason=redact(reason, secrets, fields))
            else:
                receipt.update(error_code=result["error_code"], reason=result["reason"])
            identifier = f"EV-{len(evidence) + 1:03d}"
            artifact = _attempt_artifact(prepared, result, secrets, fields, actor, proxy, decoded_body)
            if "error_code" in receipt and "transport" not in artifact:
                artifact["checks"] = {"passed": False, "error_code": receipt["error_code"], "reason": receipt["reason"]}
            else:
                artifact["checks"] = {"passed": receipt["checks_passed"]}
            _add_evidence(output, evidence, identifier, artifact, "dynamic_test",
                          json.dumps({"method": prepared.method, "url": _safe_url(prepared.url, secrets, fields),
                                      "response_status": result["status"], "complete": result["complete"],
                                      "checks_passed": receipt["checks_passed"]}, ensure_ascii=True), environment)
            receipt["evidence_refs"] = [identifier]
            replay["evidence_refs"] = [identifier]
            if not receipt["checks_passed"]:
                replay["reason"] = receipt["reason"]
        ledger.append(entry)
        receipts.append(receipt)
    dynamic = {"skill": "miniapp-dynamic", "tested_at": _now(), "environment": environment,
               "entry_mode": plan.get("entry_mode", "hypothesis"), "requests": ledger,
               "findings": [], "limitations": _LIMITATIONS}
    _private_json(output / "evidence.json", evidence)
    _private_json(output / "dynamic-test-results.json", dynamic)
    _private_json(output / "findings.json", [])
    _private_json(output / "replay-run.json", {"version": 1, "environment": environment,
                                              "results": receipts, "limitations": _LIMITATIONS})
    passed = sum(item["checks_passed"] for item in receipts)
    print(json.dumps({"requests": len(receipts), "checks_passed": passed,
                      "blocked": len(receipts) - passed, "findings": 0}))
    if setup_error:
        return 2
    return 0 if passed == len(receipts) else 3


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        return run(args.plan.resolve(), args.output_dir)
    except Exception as error:
        code, reason = _classify(error)
        # Exception strings are never emitted: they may contain URLs or credentials.
        if isinstance(error, OSError):
            code, reason = "artifact_io_error", "A private replay input or artifact could not be read or written."
        print(json.dumps({"error_code": code, "reason": reason}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
