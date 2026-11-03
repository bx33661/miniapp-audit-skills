#!/usr/bin/env python3
"""Extract a first-pass attack surface from mini program JavaScript and WXML.

Usage:
  python extract_endpoints.py --root /path/to/miniapp
  python extract_endpoints.py --root /path/to/miniapp --output surface.json

This is a discovery tool, not a complete AST analysis. It records the call
site and the URL/name expression, and marks dynamic expressions for manual
review. Use an AST pass when precision is required.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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
    """Return the index of the ')' matching text[open_index] == '('."""
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
        record = {
            "file": rel,
            "line": line_no,
            "call": call,
        }
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
        if call == "wx.request" and record["method"] is None:
            record["method"] = "GET"
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
                "src": None if "{{" in src else src,
                "src_expression": src,
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract mini program attack surface")
    parser.add_argument("--root", required=True, help="decompiled mini program root")
    parser.add_argument("--output", help="write JSON to this path instead of stdout")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2

    apis: list[dict] = []
    cloud: list[dict] = []
    navigation: list[dict] = []
    webviews: list[dict] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        if path.suffix == ".js":
            result = scan_js(path, rel)
            apis.extend(result["apis"])
            cloud.extend(result["cloud_functions"])
            navigation.extend(result["navigation"])
        elif path.suffix == ".wxml":
            webviews.extend(scan_wxml(path, rel))

    payload = {
        "root": str(root.resolve()),
        "apis": dedupe(apis, ("call", "url", "url_expression", "method")),
        "cloud_functions": dedupe(cloud, ("name", "name_expression")),
        "navigation": dedupe(navigation, ("url", "url_expression")),
        "webviews": dedupe(webviews, ("src", "src_expression")),
        "limitations": [
            "Line-based discovery; dynamic URL expressions require manual review.",
            "Use an AST pass for precise extraction and data-flow analysis.",
        ],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
