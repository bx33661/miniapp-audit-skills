"""Real loopback services for the native replay CLI scenario suite.

The fixture owns no replay logic: requests enter ordinary HTTP servers and an
optional forwarding proxy. Observations retain wire bytes only in memory; the
scenario runner writes a safe projection alongside replay's redacted evidence.
"""

import argparse
import base64
from contextlib import AbstractContextManager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import ipaddress
import json
from pathlib import Path
import secrets
import select
import signal
import socket
import ssl
import tempfile
import threading
import time
from urllib.parse import parse_qsl, urlsplit


MULTIPART = (
    b"--fixture-boundary\r\nContent-Disposition: form-data; name=\"tag\"\r\n\r\nfirst\r\n"
    b"--fixture-boundary\r\nContent-Disposition: form-data; name=\"tag\"\r\n\r\nsecond\r\n"
    b"--fixture-boundary\r\nContent-Disposition: form-data; name=\"file\"; "
    b"filename=\"sample.bin\"\r\nContent-Type: application/octet-stream\r\n\r\n"
    b"\x00\xff\x01\r\n--fixture-boundary--\r\n"
)
FORM = b"tag=first&tag=second&space=a+b&encoded=%2F%2B"
QUERY = "tag=first&tag=second&encoded=%2F%2B"
BINARY = b"\x00\xff\xfe\x80fixture-binary\x00"
AES_AAD = "fixture-business-envelope"
CASES = (
    "ownership_safe", "ownership_vulnerable", "expired_session",
    "signature_required", "signature_missing_adapter", "missing_signature_key", "signed_mutation",
    "duplicate_pairs", "multipart", "aes_roundtrip", "cookie_isolation",
    "proxy_http", "tls_verified", "tls_untrusted", "proxy_https",
    "scope_refusal", "redirect", "truncated_response", "binary_response",
    "missing_credentials", "request_limit",
)


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False


class ReplayFixture(AbstractContextManager):
    """Context manager exposing real HTTP, verified HTTPS and a local proxy."""

    def __init__(self, vulnerable=False, expired=False, observation_dir=None):
        self.vulnerable = vulnerable
        self.expired = expired
        self.observation_dir = Path(observation_dir) if observation_dir is not None else None
        self._observation_lock = threading.Lock()
        self.received = []
        self.proxy_received = []
        self._lock = threading.Lock()
        self._nonces = set()
        self._servers = []
        self._threads = []
        self._temporary = None
        self.environ = {
            "FIXTURE_A_TOKEN": "Bearer fixture-A-" + secrets.token_hex(12),
            "FIXTURE_B_TOKEN": "Bearer fixture-B-" + secrets.token_hex(12),
            "FIXTURE_A_COOKIE": "sid=fixture-A-seed",
            "FIXTURE_B_COOKIE": "sid=fixture-B-seed",
            "FIXTURE_HMAC_KEY": secrets.token_hex(32),
            "FIXTURE_AES_KEY": secrets.token_hex(32),
        }

    def __enter__(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="miniapp-replay-fixture-")
        try:
            self._make_tls()
            backend = self._backend_handler()
            http_server = self._start(backend)
            self.origin = f"http://127.0.0.1:{http_server.server_port}"
            https_server = _Server(("127.0.0.1", 0), backend)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(self.cert_file, self.key_file)
            https_server.socket = context.wrap_socket(https_server.socket, server_side=True)
            self._serve(https_server)
            self.https_origin = f"https://127.0.0.1:{https_server.server_port}"
            proxy = self._start(self._proxy_handler())
            self.proxy_url = f"http://127.0.0.1:{proxy.server_port}"
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *exc):
        for server in reversed(self._servers):
            server.shutdown()
            server.server_close()
        for thread in self._threads:
            thread.join(timeout=2)
        if self._temporary is not None:
            self._temporary.cleanup()
        return False

    def _start(self, handler):
        server = _Server(("127.0.0.1", 0), handler)
        self._serve(server)
        return server

    def _serve(self, server):
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._servers.append(server)
        self._threads.append(thread)
        thread.start()

    def _make_tls(self):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

        now = datetime.now(timezone.utc)
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Replay fixture local CA")])
        ca = (
            x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
            .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=2))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False,
                key_encipherment=False, data_encipherment=False, key_agreement=False,
                key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
            .sign(ca_key, hashes.SHA256())
        )
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
            .issuer_name(ca_name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=2))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                key_encipherment=True, data_encipherment=False, key_agreement=False,
                key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.SubjectAlternativeName([
                x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]), critical=False)
            .sign(ca_key, hashes.SHA256())
        )
        root = Path(self._temporary.name)
        self.ca_file = str(root / "ca.pem")
        self.cert_file = str(root / "server.pem")
        self.key_file = str(root / "server-key.pem")
        Path(self.ca_file).write_bytes(ca.public_bytes(serialization.Encoding.PEM))
        Path(self.cert_file).write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        Path(self.key_file).write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
        Path(self.key_file).chmod(0o600)

    def _backend_handler(self):
        fixture = self

        class Backend(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def do_GET(self):
                self._handle()

            def do_POST(self):
                self._handle()

            def _send(self, status, value, headers=(), encrypted=False):
                if isinstance(value, bytes):
                    body = value
                    content_type = "application/octet-stream"
                else:
                    body = json.dumps(value, separators=(",", ":")).encode()
                    content_type = "application/json"
                if encrypted:
                    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                    nonce = secrets.token_bytes(12)
                    body = base64.b64encode(nonce + AESGCM(bytes.fromhex(
                        fixture.environ["FIXTURE_AES_KEY"]
                    )).encrypt(nonce, body, AES_AAD.encode()))
                    content_type = "text/plain"
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                for name, value in headers:
                    self.send_header(name, value)
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                self.close_connection = True

            def _handle(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                actor = next((name for name in ("A", "B") if hmac.compare_digest(
                    self.headers.get("Authorization", ""), fixture.environ[f"FIXTURE_{name}_TOKEN"]
                )), None)
                path = urlsplit(self.path)
                cookie = self.headers.get("Cookie", "")
                cookie_actor = next((name for name in ("A", "B") if
                    f"sid=fixture-{name}-seed" in cookie or f"sid=fixture-{name}-rotated" in cookie), None)
                record = {
                    "method": self.command, "target": self.path, "path": path.path,
                    "actor": actor, "cookie_actor": cookie_actor,
                    "cookie_rotated": bool(actor and f"sid=fixture-{actor}-rotated" in cookie),
                    "body": body, "body_sha256": hashlib.sha256(body).hexdigest(),
                    "body_bytes": len(body), "signature_valid": None,
                    "encrypted": False, "status": None,
                    "application_headers": self.headers.get_all("X-Fixture-Duplicate", []),
                }
                with fixture._lock:
                    fixture.received.append(record)

                def reply(status, value, **kwargs):
                    record["status"] = status
                    if isinstance(value, dict):
                        record["business"] = value
                    fixture._persist_observations()
                    self._send(status, value, **kwargs)

                if actor is None:
                    reply(401, {"code": "AUTH_REQUIRED"})
                    return
                if path.path == "/expired" or (fixture.expired and actor == "A"):
                    reply(401, {"code": "SESSION_EXPIRED"})
                    return
                if path.path == "/redirect":
                    reply(302, {"code": "REDIRECT"}, headers=[("Location", "/redirect-target")])
                    return
                if path.path == "/redirect-target":
                    reply(200, {"redirect_followed": True})
                    return
                if path.path == "/large":
                    reply(200, b"large-response:" + b"x" * 4096)
                    return
                if path.path == "/binary":
                    reply(200, BINARY)
                    return
                if path.path in ("/session", "/cookie"):
                    if cookie_actor != actor or (path.path == "/cookie" and not record["cookie_rotated"]):
                        reply(409, {"code": "COOKIE_IDENTITY_MISMATCH"})
                    else:
                        reply(200, {"authenticated_actor": actor, "owner": actor,
                                    "cookie_actor": cookie_actor, "rotated": record["cookie_rotated"]},
                              headers=[("Set-Cookie", f"sid=fixture-{actor}-rotated; Path=/; HttpOnly")])
                    return
                if path.path in ("/signed", "/encrypted"):
                    timestamp = self.headers.get("X-Timestamp", "")
                    nonce = self.headers.get("X-Nonce", "")
                    supplied = self.headers.get("X-Signature", "")
                    canonical = "\n".join((self.command, self.path, timestamp, nonce,
                                             hashlib.sha256(body).hexdigest())).encode()
                    expected = hmac.new(fixture.environ["FIXTURE_HMAC_KEY"].encode(),
                                        canonical, hashlib.sha256).hexdigest()
                    try:
                        fresh = abs(time.time() - int(timestamp)) <= 60
                    except ValueError:
                        fresh = False
                    with fixture._lock:
                        valid = bool(fresh and nonce and nonce not in fixture._nonces and
                                     hmac.compare_digest(supplied, expected))
                        if valid:
                            fixture._nonces.add(nonce)
                    record["signature_valid"] = valid
                    record["nonce"] = nonce
                    if not valid:
                        reply(403, {"code": "SIGNATURE_REQUIRED"})
                        return
                decoded = body
                if path.path == "/encrypted":
                    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                    try:
                        envelope = base64.b64decode(body, validate=True)
                        decoded = AESGCM(bytes.fromhex(fixture.environ["FIXTURE_AES_KEY"])).decrypt(
                            envelope[:12], envelope[12:], AES_AAD.encode())
                    except Exception:
                        reply(400, {"code": "INVALID_ENVELOPE"})
                        return
                    record["encrypted"] = True
                    record["decoded_body"] = decoded
                if path.path == "/pairs":
                    accepted = (body == FORM and path.query == QUERY and
                                self.headers.get_all("X-Fixture-Duplicate", []) == ["first", "second"])
                    reply(200 if accepted else 422, {
                        "accepted": accepted, "query": parse_qsl(path.query, keep_blank_values=True),
                        "form": parse_qsl(body.decode(), keep_blank_values=True),
                    })
                    return
                if path.path == "/multipart":
                    accepted = body == MULTIPART and self.headers.get("Content-Type") == (
                        "multipart/form-data; boundary=fixture-boundary")
                    reply(200 if accepted else 422, {"accepted": accepted, "body_bytes": len(body)})
                    return
                if path.path not in ("/records", "/signed", "/encrypted"):
                    reply(404, {"code": "NOT_FOUND"})
                    return
                try:
                    record_id = (json.loads(decoded)["record"] if decoded else
                                 dict(parse_qsl(path.query))["record"])
                except (ValueError, KeyError, TypeError):
                    reply(400, {"code": "INVALID_RECORD"})
                    return
                owner = {"A-record": "A", "A-second": "A", "B-record": "B"}.get(record_id)
                if owner is None:
                    reply(404, {"code": "UNKNOWN_RECORD"})
                elif owner != actor and not fixture.vulnerable:
                    reply(403, {"code": "OWNER_DENIED", "authenticated_actor": actor})
                else:
                    reply(200, {"owner": owner, "record": record_id, "authenticated_actor": actor,
                                "business_value": "fixture-record-content"},
                          encrypted=path.path == "/encrypted")

        return Backend

    def _proxy_handler(self):
        fixture = self

        class Proxy(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def do_CONNECT(self):
                host, _, port = self.path.rpartition(":")
                allowed = urlsplit(fixture.https_origin)
                if host != allowed.hostname or int(port) != allowed.port:
                    self.send_error(403)
                    return
                with fixture._lock:
                    fixture.proxy_received.append({"method": "CONNECT", "target": self.path})
                fixture._persist_observations()
                upstream = socket.create_connection((host, int(port)), timeout=5)
                self.send_response(200, "Connection established")
                self.end_headers()
                self.connection.settimeout(5)
                upstream.settimeout(5)
                try:
                    while True:
                        readable, _, _ = select.select([self.connection, upstream], [], [], 5)
                        if not readable:
                            break
                        for source in readable:
                            data = source.recv(65536)
                            if not data:
                                return
                            (upstream if source is self.connection else self.connection).sendall(data)
                except (OSError, TimeoutError):
                    pass
                finally:
                    upstream.close()
                    self.close_connection = True

            def do_GET(self):
                self._forward()

            def do_POST(self):
                self._forward()

            def _forward(self):
                target = urlsplit(self.path)
                allowed = urlsplit(fixture.origin)
                if (target.scheme, target.hostname, target.port) != (
                        allowed.scheme, allowed.hostname, allowed.port):
                    self.send_error(403)
                    return
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                with fixture._lock:
                    fixture.proxy_received.append({"method": self.command, "target": self.path,
                                                   "body_sha256": hashlib.sha256(body).hexdigest()})
                fixture._persist_observations()
                upstream = http.client.HTTPConnection(target.hostname, target.port, timeout=5)
                try:
                    request_target = target.path or "/"
                    if target.query:
                        request_target += "?" + target.query
                    upstream.putrequest(self.command, request_target, skip_host=True, skip_accept_encoding=True)
                    for name, value in self.headers.items():
                        if name.lower() not in {"connection", "proxy-connection", "proxy-authorization"}:
                            upstream.putheader(name, value)
                    upstream.endheaders(body)
                    response = upstream.getresponse()
                    response_body = response.read()
                    self.send_response(response.status)
                    for name, value in response.getheaders():
                        if name.lower() not in {"connection", "transfer-encoding", "content-length"}:
                            self.send_header(name, value)
                    self.send_header("Content-Length", str(len(response_body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(response_body)
                finally:
                    upstream.close()
                    self.close_connection = True

        return Proxy

    def plan(self, case):
        """Build a contract plan; case verdicts are computed from observations."""
        if case not in CASES:
            raise ValueError("unknown fixture case")
        origin = self.https_origin if case in {"tls_verified", "tls_untrusted", "proxy_https"} else self.origin
        accounts = {
            actor: {"origins": [origin], "headers": [
                {"name": "Authorization", "value_env": f"FIXTURE_{actor}_TOKEN"}],
                "cookie_env": f"FIXTURE_{actor}_COOKIE"}
            for actor in ("A", "B")
        }
        scope = {"origins": [origin], "methods": ["GET", "POST"], "max_requests": 12,
                 "timeout_seconds": 5, "max_response_bytes": 65536}
        if case in {"tls_verified", "proxy_https"}:
            scope["ca_file"] = self.ca_file
        if case in {"proxy_http", "proxy_https"}:
            scope["proxy"] = self.proxy_url

        def request(identifier, actor="A", path="/records?record=A-record", **extra):
            value = {"id": identifier, "account": actor, "action": identifier,
                     "method": "GET", "url": origin + path, "expect": {"status": [200]}}
            value.update(extra)
            return value

        signature = {"type": "hmac-sha256", "key_env": "FIXTURE_HMAC_KEY"}
        requests = [request("baseline")]
        if case.startswith("ownership_"):
            requests = [request("baseline_a"), request("baseline_b", "B", "/records?record=B-record"),
                        request("probe", path="/records?record=B-record", expect={"status": [200, 403]})]
        elif case == "expired_session":
            requests = [request("expired", path="/expired"), request("blocked_a"),
                        request("independent_b", "B", "/records?record=B-record")]
        elif case == "signature_required":
            requests = [request("unsigned", path="/signed?record=A-record", expect={"status": [403]}),
                        request("independent", path="/signed?record=A-record", signature=signature)]
        elif case == "signature_missing_adapter":
            requests = [request("unsigned", path="/signed?record=A-record")]
        elif case == "missing_signature_key":
            requests = [request("blocked_signature", path="/signed?record=A-record", signature={
                "type": "hmac-sha256", "key_env": "FIXTURE_ABSENT_KEY"})]
        elif case in {"signed_mutation", "aes_roundtrip"}:
            requests = []
            for identifier, record_id in (("baseline", "A-record"), ("mutation", "A-second")):
                step = request(identifier, path=("/encrypted" if case == "aes_roundtrip" else "/signed") + "?" + QUERY,
                               method="POST", body={"type": "json", "value": {"record": record_id}},
                               signature=signature,
                               headers=[{"name": "x-TIMESTAMP", "value": "1"},
                                        {"name": "X-nONCE", "value": "stale"},
                                        {"name": "x-SIGNATURE", "value": "stale"}])
                if case == "aes_roundtrip":
                    crypto = {"type": "aes-gcm", "key_env": "FIXTURE_AES_KEY", "aad": AES_AAD}
                    step.update(encryption=crypto, response_encryption=crypto.copy())
                requests.append(step)
        elif case == "duplicate_pairs":
            requests = [request("pairs", path="/pairs?" + QUERY, method="POST",
                                headers=[{"name": "Content-Type", "value": "application/x-www-form-urlencoded"},
                                         {"name": "X-Fixture-Duplicate", "value": "first"},
                                         {"name": "X-Fixture-Duplicate", "value": "second"}],
                                body={"type": "form", "value": [["tag", "first"], ["tag", "second"],
                                                                     ["space", "a b"], ["encoded", "/+"]]})]
        elif case == "multipart":
            requests = [request("multipart", path="/multipart", method="POST",
                                headers=[{"name": "Content-Type", "value": "multipart/form-data; boundary=fixture-boundary"}],
                                body={"type": "base64", "value": base64.b64encode(MULTIPART).decode()})]
        elif case == "cookie_isolation":
            requests = [request("seed_a", path="/session"), request("seed_b", "B", "/session"),
                        request("check_a", path="/cookie"), request("check_b", "B", "/cookie")]
        elif case == "scope_refusal":
            requests = [request("out_of_scope", url=self.https_origin + "/records?record=A-record")]
        elif case == "redirect":
            requests = [request("redirect", path="/redirect", expect={"status": [302]})]
        elif case == "truncated_response":
            scope["max_response_bytes"] = 128
            requests = [request("oversized", path="/large")]
        elif case == "binary_response":
            requests = [request("binary", path="/binary")]
        elif case == "missing_credentials":
            accounts["A"]["headers"][0]["value_env"] = "FIXTURE_ABSENT_TOKEN"
            requests = [request("blocked_a"), request("independent_b", "B", "/records?record=B-record")]
        elif case == "request_limit":
            scope["max_requests"] = 1
            requests = [request("first"), request("second")]
        return {"environment": "loopback-fixture", "entry_mode": "hypothesis", "scope": scope,
                "accounts": accounts, "requests": requests}

    def observations(self):
        """Safe server receipts; no authorization values, cookies or raw bodies."""
        with self._lock:
            return [{key: value for key, value in record.items()
                     if key not in {"body", "decoded_body", "nonce"}}
                    for record in self.received]

    def _persist_observations(self):
        if self.observation_dir is None:
            return
        with self._observation_lock:
            value = {"received": self.observations(), "proxy_received": list(self.proxy_received)}
            pending = self.observation_dir / "observed.pending"
            pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            pending.chmod(0o600)
            pending.replace(self.observation_dir / "observed.json")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve a real local miniapp audit target")
    parser.add_argument("--serve", action="store_true", required=True)
    parser.add_argument("--mode", choices=("safe", "vulnerable", "expired"), default="safe")
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        arguments.output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    except OSError as exc:
        parser.exit(2, f"Cannot create new fixture output directory: {exc}\n")
    stopped = threading.Event()
    previous = {}
    for signum in (signal.SIGTERM, signal.SIGINT):
        previous[signum] = signal.signal(signum, lambda *_: stopped.set())
    try:
        with ReplayFixture(vulnerable=arguments.mode == "vulnerable",
                           expired=arguments.mode == "expired",
                           observation_dir=arguments.output_dir) as fixture:
            fixture._persist_observations()
            example = fixture.plan("ownership_safe")
            manifest = {
                "ready": True, "origin": fixture.origin, "https_origin": fixture.https_origin,
                "proxy_url": fixture.proxy_url, "ca_file": fixture.ca_file,
                "environ": fixture.environ, "accounts": example["accounts"],
                "scope": example["scope"],
                "resources": [{"record": "A-record", "owner": "A"},
                              {"record": "A-second", "owner": "A"},
                              {"record": "B-record", "owner": "B"}],
                "requests": example["requests"],
                "signature": {"type": "hmac-sha256", "key_env": "FIXTURE_HMAC_KEY"},
                "encryption": {"type": "aes-gcm", "key_env": "FIXTURE_AES_KEY", "aad": AES_AAD},
                "endpoints": ["/records?record=A-record", "/records?record=B-record",
                              "/signed", "/encrypted", "/session", "/cookie"],
            }
            print(json.dumps(manifest, separators=(",", ":")), flush=True)
            while not stopped.wait(1):
                pass
            fixture._persist_observations()
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
