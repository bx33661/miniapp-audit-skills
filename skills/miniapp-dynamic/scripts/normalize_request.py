#!/usr/bin/env python3
"""Normalize a captured mini program request into a replay template.

Usage:
  python normalize_request.py --record record.json
  python normalize_request.py --record record.json --output template.json --redact

Accepts a Reqable live-capture record or a simplified object with method, url,
headers and body. It does not send requests.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import parse_qsl

HOP_BY_HOP = {"host", "content-length", "connection", "accept-encoding"}
VOLATILE = {
    "sign",
    "signature",
    "timestamp",
    "time",
    "nonce",
    "token",
    "access_token",
    "session",
    "csrf",
}
SENSITIVE = {"authorization", "cookie", "set-cookie", "token", "access_token", "session"}


def redact(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def load_record(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: record is not valid JSON: {exc}")


def normalize(record: dict, do_redact: bool) -> dict:
    request = record.get("request") or record
    url = record.get("url") or request.get("url")
    method = request.get("method") or record.get("method") or "GET"
    body = (request.get("body") or {}).get("text") if isinstance(request.get("body"), dict) else request.get("body")
    body = body or ""

    raw_headers = request.get("headers") or {}
    headers: dict[str, str] = {}
    if isinstance(raw_headers, list):
        for item in raw_headers:
            name = item.get("name")
            value = item.get("value")
            if name and value is not None:
                headers[name] = value
    elif isinstance(raw_headers, dict):
        headers = {str(k): str(v) for k, v in raw_headers.items()}

    cleaned_headers = {}
    notes = []
    for name, value in headers.items():
        if name.lower() in HOP_BY_HOP:
            notes.append(f"dropped hop-by-hop header: {name}")
            continue
        if do_redact and name.lower() in SENSITIVE:
            value = redact(value)
        cleaned_headers[name] = value

    form_fields = []
    volatile_fields = []
    content_type = next(
        (value for name, value in headers.items() if name.lower() == "content-type"),
        "",
    )
    if body and "application/x-www-form-urlencoded" in content_type:
        for name, value in parse_qsl(body, keep_blank_values=True):
            is_volatile = name.lower() in VOLATILE
            if is_volatile:
                volatile_fields.append(name)
            field_value = redact(value) if do_redact and name.lower() in SENSITIVE else value
            form_fields.append({"name": name, "value": field_value, "volatile": is_volatile})

    if not url:
        raise SystemExit("error: record has no url")

    return {
        "source": "reqable",
        "captured_at": record.get("connection", {}).get("timestamp")
        or record.get("captured_at"),
        "request": {
            "method": method.upper(),
            "url": url,
            "headers": cleaned_headers,
            "body": body,
        },
        "form_fields": form_fields,
        "volatile_fields": volatile_fields,
        "notes": notes
        + [
            "Replay with a fresh request when possible; old requests may fail timestamp or signature checks."
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a captured request")
    parser.add_argument("--record", required=True, help="Reqable record or simplified JSON")
    parser.add_argument("--output", help="write JSON to this path instead of stdout")
    parser.add_argument("--redact", action="store_true", help="mask tokens and cookies")
    args = parser.parse_args()

    record = load_record(Path(args.record))
    template = normalize(record, args.redact)
    text = json.dumps(template, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
