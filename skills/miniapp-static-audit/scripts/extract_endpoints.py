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
from typing import NamedTuple

WEBVIEW_RE = re.compile(r"<web-view\b[^>]*\bsrc\s*=\s*(['\"])(.*?)\1", re.S)
APPID_RE = re.compile(r"wx[0-9a-f]{16}")


def infer_app_id(root: Path) -> str | None:
    for part in [root.name, *[parent.name for parent in root.parents]]:
        match = APPID_RE.search(part)
        if match:
            return match.group(0)
    return None


def load_config(root: Path) -> dict | None:
    for name in ("app.json", "app-config.json"):
        path = root / name
        if path.is_file():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
                return config if isinstance(config, dict) else None
            except json.JSONDecodeError:
                return None
    return None


class Token(NamedTuple):
    kind: str
    value: str
    start: int
    end: int


def quoted_end(text: str, start: int) -> int | None:
    """Skip one quoted token, including nested strings in template expressions."""
    quote = text[start]
    index = start + 1
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
        elif char == quote:
            return index + 1
        elif quote == "`" and text.startswith("${", index):
            index += 2
            depth = 1
            while index < len(text) and depth:
                if text[index] in "'\"`":
                    end = quoted_end(text, index)
                    if end is None:
                        return None
                    index = end
                elif text.startswith("//", index):
                    newline = text.find("\n", index)
                    index = len(text) if newline < 0 else newline + 1
                elif text.startswith("/*", index):
                    end = text.find("*/", index + 2)
                    index = len(text) if end < 0 else end + 2
                else:
                    if text[index] == "{":
                        depth += 1
                    elif text[index] == "}":
                        depth -= 1
                    index += 1
            if depth:
                return None
        else:
            index += 1
    return None


def tokenize(text: str) -> tuple[list[Token], list[str]]:
    """Lex only enough JavaScript to isolate direct calls and object properties."""
    tokens = []
    issues = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if text.startswith("//", index):
            end = text.find("\n", index)
            index = len(text) if end < 0 else end + 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                issues.append("unterminated block comment")
                break
            index = end + 2
            continue
        start = index
        kind = "symbol"
        if char in "'\"`":
            end = quoted_end(text, index)
            index = end if end is not None else len(text)
            kind = "string"
            if end is None:
                kind = "unknown"
                issues.append("unterminated quoted token")
        elif char.isalpha() or char in "_$":
            index += 1
            while index < len(text) and (text[index].isalnum() or text[index] in "_$"):
                index += 1
            kind = "identifier"
        elif char == "/" and (not tokens or tokens[-1].value in (
            "(", "[", "{", "=", ":", ",", "!", "?", ";", "return", "=>",
        )):
            # Regex literals are opaque; no API discovery inside their contents.
            index += 1
            in_class = False
            while index < len(text):
                current = text[index]
                if current == "\\":
                    index += 2
                    continue
                if current == "[":
                    in_class = True
                elif current == "]":
                    in_class = False
                elif current == "/" and not in_class:
                    index += 1
                    while index < len(text) and text[index].isalpha():
                        index += 1
                    break
                index += 1
            kind = "opaque"
            issues.append("regular-expression syntax is opaque to this first-pass lexer")
        elif text.startswith("...", index):
            index += 3
        elif text.startswith("=>", index):
            index += 2
        else:
            index += 1
        tokens.append(Token(kind, text[start:index], start, index))
    return tokens, issues


def literal(expr: str | None) -> str | None:
    if expr is None:
        return None
    tokens, issues = tokenize(expr)
    if issues or len(tokens) != 1 or tokens[0].kind != "string":
        return None
    value = tokens[0].value
    if value[0] == "`" and "${" in value:
        return None
    content = value[1:-1]
    decoded = []
    index = 0
    escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f",
               "v": "\v", "0": "\0", "\\": "\\", "'": "'", '"': '"',
               "`": "`", "/": "/", "$": "$"}
    while index < len(content):
        char = content[index]
        if char != "\\":
            if char in "\r\n" and value[0] != "`":
                return None
            decoded.append(char)
            index += 1
            continue
        index += 1
        if index >= len(content):
            return None
        char = content[index]
        if char in "xu":
            count = 2 if char == "x" else 4
            digits = content[index + 1:index + 1 + count]
            if len(digits) != count or not re.fullmatch(r"[0-9a-fA-F]+", digits):
                return None
            decoded.append(chr(int(digits, 16)))
            index += count + 1
        elif char in escapes:
            decoded.append(escapes[char])
            index += 1
        else:
            return None
    return "".join(decoded)


def delimiter_pairs(tokens: list[Token]) -> tuple[dict[int, int], bool]:
    stack = []
    pairs = {}
    valid = True
    closing = {")": "(", "]": "[", "}": "{"}
    for index, token in enumerate(tokens):
        if token.kind != "symbol":
            continue
        if token.value in ("(", "[", "{"):
            stack.append(index)
        elif token.value in closing:
            if not stack or tokens[stack[-1]].value != closing[token.value]:
                valid = False
                continue
            pairs[stack.pop()] = index
    return pairs, valid and not stack


def object_properties(text: str, tokens: list[Token], pairs: dict[int, int],
                      open_index: int) -> tuple[dict[str, str], str | None]:
    close = pairs.get(open_index)
    if close is None:
        return {}, "unbalanced call delimiters"
    start = open_index + 1
    if start >= close or tokens[start].value != "{" or tokens[start].kind != "symbol":
        return {}, "options are not a direct object literal"
    end = pairs.get(start)
    if end is None or end >= close or any(token.value != "," for token in tokens[end + 1:close]):
        return {}, "options are not an isolated object literal"
    properties = {}
    index = start + 1
    while index < end:
        if tokens[index].value == ",":
            index += 1
            continue
        key = tokens[index]
        name = key.value if key.kind == "identifier" else literal(key.value)
        if name is None:
            return {}, "computed or spread properties can override endpoint options"
        value_start = index + 2
        if index + 1 >= end or tokens[index + 1].value != ":":
            return {}, "shorthand, accessors or object methods are unresolved"
        index = value_start
        while index < end:
            token = tokens[index]
            if token.kind == "symbol" and token.value in ("(", "[", "{"):
                nested_end = pairs.get(index)
                if nested_end is None or nested_end >= end:
                    return {}, "unbalanced property expression"
                index = nested_end + 1
            elif token.kind == "symbol" and token.value == ",":
                break
            else:
                index += 1
        if value_start == index:
            return {}, "empty property expression"
        properties[name] = text[tokens[value_start].start:tokens[index - 1].end]
    return properties, None


def scan_js(path: Path, rel: str) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    tokens, lex_issues = tokenize(text)
    pairs, balanced = delimiter_pairs(tokens)
    limitations = [f"{rel}: {issue}" for issue in lex_issues]
    if not balanced:
        limitations.append(f"{rel}: unbalanced delimiters; affected calls remain unresolved")
    apis, cloud, navigation = [], [], []
    calls = {
        "wx.request", "wx.uploadFile", "wx.downloadFile", "wx.connectSocket",
        "wx.cloud.callFunction", "wx.navigateTo", "wx.redirectTo", "wx.switchTab", "wx.reLaunch",
    }
    for index, token in enumerate(tokens):
        if token.kind != "identifier" or token.value != "wx":
            continue
        if index and tokens[index - 1].value == ".":
            continue
        parts = ["wx"]
        cursor = index + 1
        while cursor + 1 < len(tokens) and tokens[cursor].value == "." and tokens[cursor + 1].kind == "identifier":
            parts.append(tokens[cursor + 1].value)
            cursor += 2
        call = ".".join(parts)
        if call not in calls or cursor >= len(tokens) or tokens[cursor].value != "(":
            continue
        line_no = text.count("\n", 0, token.start) + 1
        properties, issue = object_properties(text, tokens, pairs, cursor)
        record = {"file": rel, "line": line_no, "call": call}
        target = "name" if call == "wx.cloud.callFunction" else "url"
        expression = properties.get(target)
        value = literal(expression)
        record[target] = value
        record[f"{target}_expression"] = expression
        record["dynamic"] = value is None
        if issue or value is None:
            reason = issue or f"top-level {target} is missing or dynamic: {expression!r}"
            limitations.append(f"{rel}:{line_no}: {call}: {reason}")
        if call == "wx.cloud.callFunction":
            cloud.append(record)
        elif call in ("wx.navigateTo", "wx.redirectTo", "wx.switchTab", "wx.reLaunch"):
            navigation.append(record)
        else:
            method_expr = properties.get("method")
            method = literal(method_expr)
            record["method"] = method.upper() if method else "UNKNOWN"
            record["method_expression"] = method_expr
            if record["method"] == "UNKNOWN":
                limitations.append(f"{rel}:{line_no}: {call}: method unknown: {method_expr!r}")
            apis.append(record)
    return {"apis": apis, "cloud_functions": cloud, "navigation": navigation,
            "limitations": limitations}


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


def aggregate(records: list[dict], target: str, include_method: bool = False) -> list[dict]:
    grouped = {}
    for record in records:
        value = record.get(target)
        key = (record["call"], value is None,
               value if value is not None else record.get(f"{target}_expression"))
        if include_method:
            key += (record["method"], record.get("method_expression") if record["method"] == "UNKNOWN" else None)
        if key not in grouped:
            grouped[key] = dict(record, locations=[])
        grouped[key]["locations"].append({"file": record["file"], "line": record["line"]})
    return list(grouped.values())


def api_record(record: dict, index: int) -> dict:
    call = record["call"]
    api_type = {"wx.connectSocket": "websocket", "wx.uploadFile": "upload",
                "wx.downloadFile": "download"}.get(call, "http")
    url = record.get("url")
    host = ""
    if url is not None:
        try:
            parsed = urlparse(url)
            if parsed.scheme.lower() in ("http", "https", "ws", "wss"):
                host = parsed.netloc
        except ValueError:
            pass
    return {
        "id": f"API-{index:03d}",
        "type": api_type,
        "method": record["method"],
        "url": url if url is not None else record.get("url_expression") or "",
        "url_expression": record.get("url_expression"),
        "dynamic": record["dynamic"],
        "call": call,
        "domain": host,
        "locations": record["locations"],
    }


def cloud_record(record: dict, index: int) -> dict:
    return {
        "id": f"CF-{index:03d}",
        "name": record["name"] if record["name"] is not None else record.get("name_expression") or "",
        "name_expression": record.get("name_expression"),
        "dynamic": record["dynamic"],
        "params": [],
        "locations": record["locations"],
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

    loaded_config = load_config(root)
    config_loaded = loaded_config is not None
    config = loaded_config or {}
    apis: list[dict] = []
    cloud: list[dict] = []
    navigation: list[dict] = []
    webviews: list[dict] = []
    files_scanned = 0
    limitations = [
        "First-pass lexical discovery of direct wx calls; no complete JavaScript AST or execution.",
        "Aliases, wrappers, computed calls, option objects held in variables and runtime values require manual review.",
        "Framework, third-party ownership, cloud database use, sensitive APIs, request wrappers and permission usage are not assessed.",
    ]
    if not config_loaded:
        limitations.append("App configuration was not successfully read; declared material counts are unknown.")

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
            limitations.extend(result["limitations"])
        elif path.suffix == ".wxml":
            files_scanned += 1
            webviews.extend(scan_wxml(path, rel))

    apis = [api_record(item, i + 1) for i, item in enumerate(aggregate(apis, "url", True))]
    cloud = [cloud_record(item, i + 1) for i, item in enumerate(aggregate(cloud, "name"))]
    navigation = aggregate(navigation, "url")

    domains = {}
    for item in apis:
        host = item.get("domain")
        if not host:
            continue
        protocol = urlparse(item["url"]).scheme.lower()
        domain_type = {"websocket": "socket", "upload": "upload", "download": "download"}.get(item["type"], "request")
        key = (host, protocol, domain_type)
        if key in domains:
            continue
        domains[key] = {
            "domain": host,
            "protocol": protocol,
            "type": domain_type,
            "source": "code",
            "first_seen": item["locations"][0],
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
        "skill": "miniapp-static-audit",
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(root.resolve()),
        "metadata": {
            "app_id": args.app_id or config.get("appId") or config.get("appid") or infer_app_id(root),
            "app_name": config.get("appName") or "",
            "framework": "unknown",
            "pages_count": (
                len(config.get("pages") or []) + sum(len(sub.get("pages") or []) for sub in subpackages)
            ) if config_loaded else None,
            "subpackages_count": len(subpackages) if config_loaded else None,
            "plugins_count": len(plugins) if config_loaded else None,
        },
        "apis": apis,
        "cloud_functions": cloud,
        "permissions": {
            "declared": list(permissions.keys()),
            "required_private_infos": config.get("requiredPrivateInfos") or [],
        },
        "domains": list(domains.values()),
        "webviews": webview_records,
        "navigation": navigation,
        "limitations": limitations,
        "statistics": {
            "total_apis": len(apis),
            "http_apis": sum(1 for item in apis if item["type"] == "http"),
            "websocket_apis": sum(1 for item in apis if item["type"] == "websocket"),
            "cloud_functions": len(cloud),
            "unique_domains": len({item["domain"] for item in domains.values()}),
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
