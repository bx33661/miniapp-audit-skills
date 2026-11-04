"""Account-isolated request preparation for the documented replay-plan protocol.

Bodies from file/base64 remain exact bytes, including multipart boundaries.  The
only crypto adapters here are the explicit HMAC canonicalization and AES-GCM
base64 envelope in the replay contract; target scripts are never evaluated.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import http.cookiejar
import json
import re
import secrets as randomness
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit
from urllib.request import Request


class ReplayError(Exception):
    """A public, value-free error suitable for redacted replay receipts."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class AccountState:
    name: str
    origins: set[str]
    headers: list[tuple[str, str]]
    cookies: http.cookiejar.CookieJar
    secrets: list[str]
    expired_status: set[int]
    expired_json: list[dict]
    blocked_reason: str | None = None
    _methods: set[str] | None = field(default=None, repr=False)


@dataclass
class PreparedRequest:
    id: str
    account: str
    action: str
    source_ref: str
    method: str
    url: str
    headers: list[tuple[str, str]]
    body: bytes
    expect: dict
    config: dict
    secrets: list[str]


_HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_CONTROLLED_HEADERS = {"host", "content-length", "transfer-encoding", "connection"}
_CAPTURED_CREDENTIAL_HEADERS = {
    "authorization", "proxy-authorization", "cookie", "x-api-key", "api-key",
    "x-auth-token", "x-access-token", "x-session-token",
}
_REDACT_FIELDS = {
    "authorization", "proxyauthorization", "cookie", "setcookie", "password",
    "passwd", "pwd", "secret", "appsecret", "clientsecret", "privatekey",
    "apikey", "accesskey", "accesskeysecret", "token", "accesstoken",
    "refreshtoken", "idtoken", "session", "sessionid", "sessionkey",
    "signature", "sign", "phone", "phonenumber", "mobile", "mobilenumber",
    "email", "emailaddress", "idcard", "idcardnumber", "identitynumber",
    "nationalid", "passport", "realname", "fullname", "address",
    "openid", "unionid",
}


def _origin(url: str, *, origin_only: bool = False) -> str:
    """Normalize equivalent origins without decoding request paths or queries."""
    try:
        if not isinstance(url, str) or not url or not url.isascii():
            raise ValueError
        if any(ord(char) <= 32 or ord(char) == 127 for char in url):
            raise ValueError
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError
        if parsed.username is not None or parsed.password is not None:
            raise ValueError
        if "#" in url or "\\" in url or parsed.netloc.endswith(":"):
            raise ValueError
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError
        if origin_only and (parsed.path not in ("", "/") or "?" in url):
            raise ValueError
        hostname = parsed.hostname.lower()
        host = f"[{hostname}]" if ":" in hostname else hostname
        port = parsed.port
        default_port = 443 if parsed.scheme == "https" else 80
        authority = host if port is None or port == default_port else f"{host}:{port}"
        return f"{parsed.scheme}://{authority}"
    except (TypeError, ValueError):
        raise ReplayError("invalid_origin", "An HTTP origin or URL is invalid.") from None


def _header(name: str, value: str) -> tuple[str, str]:
    if not isinstance(name, str) or not _HEADER_NAME.fullmatch(name):
        raise ReplayError("invalid_header", "A request header name is invalid.")
    if not isinstance(value, str) or any(
        ord(char) < 32 and char != "\t" or ord(char) == 127 for char in value
    ):
        raise ReplayError("invalid_header", "A request header value is invalid.")
    try:
        value.encode("latin-1")
    except UnicodeEncodeError:
        raise ReplayError("invalid_header", "A request header value is not HTTP/1.1 encodable.") from None
    if name.lower() in _CONTROLLED_HEADERS:
        raise ReplayError("controlled_header", "A transport-controlled header cannot be supplied.")
    return name, value


def _env_value(name: str, environ: Mapping[str, str]) -> str:
    if not isinstance(name, str) or not name:
        raise ReplayError("credential_missing", "A required named environment credential is missing.")
    value = environ.get(name)
    if not isinstance(value, str) or not value:
        raise ReplayError("credential_missing", "A required named environment credential is missing.")
    return value


def _reject_constant(_value: str) -> None:
    raise ValueError("Non-finite JSON number")


def load_plan(path: Path) -> dict:
    """Validate a local plan with the bundled, non-network JSON schema."""
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        raise ReplayError("dependency_missing", "Plan validation requires the jsonschema dependency.") from None
    schema_path = Path(__file__).resolve().parents[1] / "assets" / "replay-plan.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    except (OSError, UnicodeError, ValueError):
        raise ReplayError("schema_unavailable", "The bundled replay plan schema could not be loaded.") from None

    # A bundled schema is the sole authority; never resolve remote references.
    def check_refs(node: Any) -> None:
        if isinstance(node, dict):
            if "$ref" in node and not str(node["$ref"]).startswith("#"):
                raise ReplayError("schema_invalid", "The bundled schema contains an external reference.")
            for child in node.values():
                check_refs(child)
        elif isinstance(node, list):
            for child in node:
                check_refs(child)

    check_refs(schema)
    try:
        Draft7Validator.check_schema(schema)
    except Exception:
        raise ReplayError("schema_invalid", "The bundled replay plan schema is invalid.") from None
    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=_reject_constant)
    except (OSError, UnicodeError, ValueError):
        raise ReplayError("plan_invalid", "The replay plan could not be read as JSON.") from None
    if not Draft7Validator(schema).is_valid(plan):
        raise ReplayError("plan_invalid", "The replay plan does not satisfy the bundled schema.")
    scope = plan["scope"]
    origins = {_origin(origin, origin_only=True) for origin in scope["origins"]}
    if len(plan["requests"]) > scope["max_requests"]:
        raise ReplayError("request_limit", "The replay plan exceeds its request limit.")
    for profile in plan["accounts"].values():
        allowed = {_origin(origin, origin_only=True) for origin in profile["origins"]}
        if not allowed <= origins:
            raise ReplayError("account_scope", "An account origin is outside the authorized scope.")
    identifiers: set[str] = set()
    for step in plan["requests"]:
        if step["id"] in identifiers:
            raise ReplayError("duplicate_request", "Replay request identifiers must be unique.")
        identifiers.add(step["id"])
        if step["account"] not in plan["accounts"]:
            raise ReplayError("unknown_account", "A replay request names an unknown account.")
    proxy = scope.get("proxy")
    if proxy is not None:
        proxy_origin = _origin(proxy, origin_only=True)
        if not proxy_origin.startswith("http://") or urlsplit(proxy).port is None:
            raise ReplayError("proxy_invalid", "The explicit HTTP proxy must include its port.")
    return plan


def _seed_cookies(account: AccountState, raw: str) -> None:
    """Seed once at account construction; server updates own the jar thereafter."""
    _header("Cookie", raw)
    parsed: SimpleCookie = SimpleCookie()
    try:
        parsed.load(raw)
    except CookieError:
        raise ReplayError("credential_invalid", "An account cookie credential is invalid.") from None
    if not parsed or any(any(morsel.values()) for morsel in parsed.values()):
        raise ReplayError("credential_invalid", "An account cookie credential is invalid.")
    domains: dict[str, bool] = {}
    for origin in sorted(account.origins):
        # CookieJar uses an effective .local hostname for single-label hosts.
        domain = http.cookiejar.eff_request_host(Request(origin + "/"))[1]
        secure = urlsplit(origin).scheme == "https"
        domains[domain] = domains.get(domain, True) and secure
    for domain, secure in domains.items():
        for name, morsel in parsed.items():
            account.cookies.set_cookie(http.cookiejar.Cookie(
                version=0, name=name, value=morsel.coded_value,
                port=None, port_specified=False,
                domain=domain, domain_specified=False, domain_initial_dot=False,
                path="/", path_specified=True, secure=secure,
                expires=None, discard=True, comment=None, comment_url=None,
                rest={}, rfc2109=False,
            ))
    account.secrets.extend(morsel.value for morsel in parsed.values() if morsel.value)
    account.secrets.extend(morsel.coded_value for morsel in parsed.values() if morsel.coded_value)


def build_accounts(plan: dict, environ: Mapping[str, str]) -> dict[str, AccountState]:
    accounts: dict[str, AccountState] = {}
    scope_origins = {_origin(origin, origin_only=True) for origin in plan["scope"]["origins"]}
    for name, profile in plan["accounts"].items():
        policy = http.cookiejar.DefaultCookiePolicy(
            strict_ns_domain=http.cookiejar.DefaultCookiePolicy.DomainStrictNonDomain,
        )
        account = AccountState(
            name=name,
            origins=set(),
            headers=[],
            cookies=http.cookiejar.CookieJar(policy),
            secrets=[],
            expired_status=set(profile.get("expired_status", [401])),
            expired_json=profile.get("expired_json", []),
            _methods=set(plan["scope"]["methods"]),
        )
        accounts[name] = account
        try:
            account.origins = {_origin(origin, origin_only=True) for origin in profile["origins"]}
            if not account.origins <= scope_origins:
                raise ReplayError("account_scope", "An account origin is outside the authorized scope.")
            for config in profile.get("headers", []):
                value = _env_value(config["value_env"], environ)
                account.secrets.append(value)
                pair = _header(config["name"], value)
                if pair[0].lower() in {"cookie", "proxy-authorization"}:
                    raise ReplayError("credential_invalid", "Cookie and proxy credentials cannot be account headers.")
                account.headers.append(pair)
            if "cookie_env" in profile:
                value = _env_value(profile["cookie_env"], environ)
                account.secrets.append(value)
                _seed_cookies(account, value)
        except ReplayError as exc:
            account.blocked_reason = exc.message
            account.headers.clear()
            account.cookies.clear()
    return accounts


def _body(config: dict, base_dir: Path) -> tuple[bytes, str | None]:
    kind = config.get("type", "none")
    try:
        if kind == "none":
            return b"", None
        if kind == "text":
            return config["value"].encode("utf-8"), "text/plain; charset=utf-8"
        if kind == "json":
            return json.dumps(config["value"], ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"), "application/json"
        if kind == "form":
            return urlencode([tuple(pair) for pair in config["value"]], doseq=False, encoding="utf-8", errors="strict").encode("ascii"), "application/x-www-form-urlencoded"
        if kind == "base64":
            return base64.b64decode(config["value"], validate=True), None
        if kind == "file":
            path = Path(config["path"])
            return (path if path.is_absolute() else base_dir / path).read_bytes(), None
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        raise ReplayError("body_invalid", "A replay body could not be prepared from its declared source.") from None
    raise ReplayError("body_unsupported", "The declared replay body type is unsupported.")


def _aes(config: dict, environ: Mapping[str, str]) -> tuple[Any, bytes, list[str]]:
    if config.get("type") != "aes-gcm":
        raise ReplayError("encryption_unsupported", "The declared encryption protocol requires an explicit supported adapter.")
    raw = _env_value(config.get("key_env"), environ)
    if not re.fullmatch(r"(?:[0-9A-Fa-f]{32}|[0-9A-Fa-f]{48}|[0-9A-Fa-f]{64})", raw):
        raise ReplayError("encryption_key_invalid", "An AES-GCM key must be a hex-encoded 16, 24, or 32 byte key.")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise ReplayError("dependency_missing", "AES-GCM requires the cryptography dependency.") from None
    try:
        aad = config.get("aad", "").encode("utf-8")
        return AESGCM(bytes.fromhex(raw)), aad, [raw]
    except (TypeError, ValueError, AttributeError, UnicodeError):
        raise ReplayError("encryption_invalid", "The declared AES-GCM configuration is invalid.") from None


def _sign(config: dict, method: str, url: str, body: bytes, environ: Mapping[str, str]) -> tuple[list[tuple[str, str]], list[str]]:
    if config.get("type") != "hmac-sha256":
        raise ReplayError("signature_unsupported", "The declared signature protocol requires an explicit supported adapter.")
    raw = _env_value(config.get("key_env"), environ)
    encoding = config.get("key_encoding", "utf8")
    try:
        if encoding == "utf8":
            key = raw.encode("utf-8")
        elif encoding == "hex":
            if not re.fullmatch(r"(?:[0-9A-Fa-f]{2})+", raw):
                raise ValueError
            key = bytes.fromhex(raw)
        elif encoding == "base64":
            key = base64.b64decode(raw, validate=True)
        else:
            raise ValueError
        if not key:
            raise ValueError
    except (ValueError, UnicodeError):
        raise ReplayError("signature_key_invalid", "The HMAC key does not match its declared encoding.") from None
    timestamp = str(int(time.time()))
    nonce = randomness.token_hex(16)
    parsed = urlsplit(url)
    target = (parsed.path or "/") + ("?" + parsed.query if "?" in url else "")
    canonical = "\n".join((method, target, timestamp, nonce, hashlib.sha256(body).hexdigest())).encode("utf-8")
    signature = hmac.new(key, canonical, hashlib.sha256).hexdigest()
    headers = [
        _header(config.get("timestamp_header", "X-Timestamp"), timestamp),
        _header(config.get("nonce_header", "X-Nonce"), nonce),
        _header(config.get("signature_header", "X-Signature"), signature),
    ]
    if len({name.lower() for name, _ in headers}) != 3:
        raise ReplayError("signature_invalid", "HMAC derived header names must be distinct.")
    if any(name.lower() in _CAPTURED_CREDENTIAL_HEADERS for name, _ in headers):
        raise ReplayError("signature_invalid", "HMAC derived headers cannot replace identity credentials.")
    return headers, [raw, signature]


def prepare_request(step: dict, account: AccountState, base_dir: Path, environ: Mapping[str, str]) -> PreparedRequest:
    if account.blocked_reason is not None:
        raise ReplayError("account_blocked", account.blocked_reason)
    if step["account"] != account.name:
        raise ReplayError("account_mismatch", "The replay request does not match its account state.")
    origin = _origin(step["url"])
    if origin not in account.origins:
        raise ReplayError("scope_refused", "The request origin is outside the account's authorized origins.")
    method = step["method"]
    if not isinstance(method, str) or not _HEADER_NAME.fullmatch(method) or method != method.upper():
        raise ReplayError("method_invalid", "The request method must be an uppercase HTTP token.")
    if account._methods is None:
        raise ReplayError("scope_unbound", "The account must be initialized with an explicit method scope.")
    if method not in account._methods:
        raise ReplayError("scope_refused", "The request method is outside the authorized scope.")
    headers: list[tuple[str, str]] = []
    secret_values = list(account.secrets)
    actor_header_names = {name.lower() for name, _ in account.headers}
    for config in step.get("headers", []):
        name, value = _header(config["name"], config["value"])
        if name.lower() in _CAPTURED_CREDENTIAL_HEADERS or name.lower() in actor_header_names:
            raise ReplayError("captured_credential", "Captured credentials must be supplied through the account profile.")
        headers.append((name, value))
    headers.extend(account.headers)
    body, content_type = _body(step.get("body", {"type": "none"}), Path(base_dir))
    if content_type and not any(name.lower() == "content-type" for name, _ in headers):
        headers.append(("Content-Type", content_type))
    if "response_encryption" in step:
        _, _, loaded = _aes(step["response_encryption"], environ)
        secret_values.extend(loaded)
    if "encryption" in step:
        cipher, aad, loaded = _aes(step["encryption"], environ)
        secret_values.extend(loaded)
        nonce = randomness.token_bytes(12)
        try:
            body = base64.b64encode(nonce + cipher.encrypt(nonce, body, aad))
        except (ValueError, OverflowError):
            raise ReplayError("encryption_failed", "The request could not be encoded with the declared AES-GCM envelope.") from None
    if "signature" in step:
        derived, loaded = _sign(step["signature"], method, step["url"], body, environ)
        derived_names = {name.lower() for name, _ in derived}
        if derived_names & actor_header_names:
            raise ReplayError("signature_invalid", "HMAC derived headers collide with account credential headers.")
        headers = [(name, value) for name, value in headers if name.lower() not in derived_names]
        headers.extend(derived)
        secret_values.extend(loaded)
    return PreparedRequest(
        id=step["id"], account=account.name, action=step["action"],
        source_ref=step.get("source_ref", "plan:" + step["id"]), method=method,
        url=step["url"], headers=headers, body=body, expect=step["expect"],
        config=step, secrets=secret_values,
    )


def decode_response_body(step: dict, body: bytes, environ: Mapping[str, str]) -> bytes:
    if "response_encryption" not in step:
        return body
    cipher, aad, _ = _aes(step["response_encryption"], environ)
    try:
        envelope = base64.b64decode(body, validate=True)
        if len(envelope) < 28:
            raise ValueError
        from cryptography.exceptions import InvalidTag
        try:
            return cipher.decrypt(envelope[:12], envelope[12:], aad)
        except InvalidTag:
            raise ReplayError("decryption_failed", "The response failed AES-GCM envelope authentication.") from None
    except (ValueError, binascii.Error, OverflowError):
        raise ReplayError("decryption_failed", "The response is not a valid declared AES-GCM envelope.") from None


def redact(value: Any, secrets: Sequence[str], field_names: Sequence[str] = ()) -> Any:
    """Redact known text secrets and named JSON fields, preserving owner markers.

    This is intentionally not a universal PII detector. Header/query/form
    credential masking belongs to the evidence renderer as specified separately.
    """
    names = _REDACT_FIELDS | {re.sub(r"[^a-z0-9]", "", name.lower()) for name in field_names}
    known = sorted({secret for secret in secrets if isinstance(secret, str) and secret}, key=len, reverse=True)

    def text(raw: str) -> str:
        for secret in known:
            raw = raw.replace(secret, "[REDACTED]")
        return raw

    def visit(item: Any) -> Any:
        if isinstance(item, dict):
            return {
                text(key) if isinstance(key, str) else key:
                "[REDACTED]" if isinstance(key, str) and re.sub(r"[^a-z0-9]", "", key.lower()) in names else visit(child)
                for key, child in item.items()
            }
        if isinstance(item, (list, tuple)):
            return [visit(child) for child in item]
        if isinstance(item, str):
            return text(item)
        return item

    return visit(value)
