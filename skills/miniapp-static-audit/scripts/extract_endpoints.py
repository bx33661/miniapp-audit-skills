#!/usr/bin/env python3
"""Extract a first-pass attack surface from mini program JavaScript and WXML.

Usage:
  python extract_endpoints.py --root /path/to/miniapp
  python extract_endpoints.py --root /path/to/miniapp --output surface.json

The output follows assets/attack-surface-output.schema.json. It is a discovery
tool, not a complete AST analysis; dynamic expressions and wrapped calls need
manual review.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

CALL_RE = re.compile(
    r"\b("
    r"wx\.request|wx\.uploadFile|wx\.downloadFile|wx\.connectSocket|"
    r"wx\.cloud\.callFunction|"
    r"wx\.navigateTo|wx\.redirectTo|wx\.switchTab|wx\.reLaunch"
    r")\s*\("
)
URL_EXPR_RE = re.compile(r"\burl\s*:\s*([^,\n}]+)")
NAME_EXPR_RE = re.compile(r"\bname\s*:\s*([^,\n}]+)")
METHOD_RE = re.compile(r"\bmethod\s*:\s*['\"`]([^'\"`]+)['\"`]")
WEBVIEW_RE = re.compile(r"<web-view\b[^>]*\bsrc\s*=\s*(['\"])(.*?)\1", re.S)
APPID_RE = re.compile(r"wx[0-9a-f]{16}")


def infer_app_id(root: Path) -> str | None:
    for part in [root.name, *[parent.name for parent in root.parents]]:
        match = APPID_RE.search(part)
        if match:
            return match.group(0)
    return None


def load_config(root: Path) -> dict:
    for name in ("app.json", "app-config.json"):
        path = root / name
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
    return {}


def literal(expr: str | None) -> str | None:
    if expr is None:
        return None
    value = expr.strip().rstrip(",;")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"`":
        return value[1:-1]
    return None


def is_dynamic(expr: str | None) -> bool:
    return expr is not None and literal(expr) is None


def matching_paren(text: str, open_index: int) -> int:
    depth = 0
    quote = None
    escape = False
    for index in range(open_index, len(text)):
        char = text[index]
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            continue
        if char in "'\"`":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return min(len(text), open_index + 2000)


def scan_js(path: Path, rel: str) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    apis: list[dict] = []
    cloud: list[dict] = []
    navigation: list[dict] = []

    for match in CALL_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        open_index = match.end() - 1
        close_index = matching_paren(text, open_index)
        block = text[open_index:close_index + 1]
        call = match.group(1)
        url_expr = URL_EXPR_RE.search(block)
        name_expr = NAME_EXPR_RE.search(block)
        method_match = METHOD_RE.search(block)
        record = {"file": rel, "line": line_no, "call": call}
        if call == "wx.cloud.callFunction":
            record["name"] = literal(name_expr.group(1)) if name_expr else None
            record["name_expression"] = name_expr.group(1).strip() if name_expr else None
            cloud.append(record)
            continue
        if call in ("wx.navigateTo", "wx.redirectTo", "wx.switchTab", "wx.reLaunch"):
            record["url"] = literal(url_expr.group(1)) if url_expr else None
            record["url_expression"] = url_expr.group(1).strip() if url_expr else None
            record["dynamic"] = is_dynamic(url_expr.group(1) if url_expr else None)
            navigation.append(record)
            continue
        record["url"] = literal(url_expr.group(1)) if url_expr else None
        record["url_expression"] = url_expr.group(1).strip() if url_expr else None
        record["dynamic"] = is_dynamic(url_expr.group(1) if url_expr else None)
        record["method"] = method_match.group(1).upper() if method_match else None
        apis.append(record)
    return {"apis": apis, "cloud_functions": cloud, "navigation": navigation}


def scan_wxml(path: Path, rel: str) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    records = []
    for match in WEBVIEW_RE.finditer(text):
        src = match.group(2)
        line_no = text.count("\n", 0, match.start()) + 1
        records.append(
            {
                "file": rel,
                "line": line_no,
                "src": src,
                "dynamic": "{{" in src,
            }
        )
    return records


def dedupe(records: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    seen = set()
    result = []
    for record in records:
        key = tuple(record.get(field) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def api_record(record: dict, index: int) -> dict:
    call = record["call"]
    if call == "wx.connectSocket":
        api_type, method = "websocket", "CALL"
    elif call == "wx.uploadFile":
        api_type, method = "upload", "POST"
    elif call == "wx.downloadFile":
        api_type, method = "download", "GET"
    else:
        api_type, method = "http", record.get("method") or "GET"
    url = record.get("url") or record.get("url_expression") or ""
    host = urlparse(url).netloc if url.startswith(("http://", "https://", "ws://", "wss://")) else ""
    return {
        "id": f"API-{index:03d}",
        "type": api_type,
        "method": method,
        "url": url,
        "url_expression": record.get("url_expression"),
        "dynamic": record.get("dynamic", False),
        "call": call,
        "domain": host,
        "locations": [{"file": record["file"], "line": record["line"]}],
    }


def cloud_record(record: dict, index: int) -> dict:
    return {
        "id": f"CF-{index:03d}",
        "name": record.get("name") or record.get("name_expression") or "",
        "name_expression": record.get("name_expression"),
        "params": [],
        "locations": [{"file": record["file"], "line": record["line"]}],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract mini program attack surface")
    parser.add_argument("--root", required=True, help="decompiled mini program root")
    parser.add_argument("--app-id", help="known mini program appid")
    parser.add_argument("--output", help="write JSON to this path instead of stdout")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2

    config = load_config(root)
    apis: list[dict] = []
    cloud: list[dict] = []
    navigation: list[dict] = []
    webviews: list[dict] = []
    files_scanned = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        if path.suffix == ".js":
            files_scanned += 1
            result = scan_js(path, rel)
            apis.extend(result["apis"])
            cloud.extend(result["cloud_functions"])
            navigation.extend(result["navigation"])
        elif path.suffix == ".wxml":
            files_scanned += 1
            webviews.extend(scan_wxml(path, rel))

    apis = [api_record(item, i + 1) for i, item in enumerate(dedupe(apis, ("call", "url", "url_expression", "method")))]
    cloud = [cloud_record(item, i + 1) for i, item in enumerate(dedupe(cloud, ("name", "name_expression")))]
    navigation = dedupe(navigation, ("url", "url_expression"))
    webviews = dedupe(webviews, ("file", "line", "src"))

    domains = {}
    for item in apis:
        host = item.get("domain")
        if not host or host in domains:
            continue
        protocol = "wss" if item["type"] == "websocket" else "https"
        domains[host] = {
            "domain": host,
            "protocol": protocol,
            "type": "socket" if item["type"] == "websocket" else "request",
            "source": "code",
            "first_seen": item["locations"][0],
            "is_third_party": False,
        }

    webview_records = [
        {
            "page": item["file"],
            "src_type": "dynamic" if item["dynamic"] else "static",
            "src": item["src"],
            "location": {"file": item["file"], "line": item["line"]},
        }
        for item in webviews
    ]

    subpackages = config.get("subPackages") or config.get("subpackages") or []
    plugins = config.get("plugins") or {}
    permissions = config.get("permission") or {}
    payload = {
        "skill": "attack-surface",
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(root.resolve()),
        "metadata": {
            "app_id": args.app_id or config.get("appId") or config.get("appid") or infer_app_id(root) or "unknown",
            "app_name": config.get("appName") or "",
            "framework": "native",
            "pages_count": len(config.get("pages") or []),
            "subpackages_count": len(subpackages),
            "plugins_count": len(plugins),
        },
        "apis": apis,
        "cloud_functions": cloud,
        "cloud_database": [],
        "sensitive_apis": [],
        "permissions": {
            "declared": list(permissions.keys()),
            "required_private_infos": config.get("requiredPrivateInfos") or [],
            "used": [],
            "undeclared": [],
        },
        "domains": list(domains.values()),
        "webviews": webview_records,
        "request_wrappers": [],
        "navigation": navigation,
        "statistics": {
            "total_apis": len(apis),
            "http_apis": sum(1 for item in apis if item["type"] == "http"),
            "websocket_apis": sum(1 for item in apis if item["type"] == "websocket"),
            "cloud_functions": len(cloud),
            "cloud_database_collections": 0,
            "sensitive_apis": 0,
            "unique_domains": len(domains),
            "third_party_domains": 0,
            "webviews": len(webview_records),
            "files_scanned": files_scanned,
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
