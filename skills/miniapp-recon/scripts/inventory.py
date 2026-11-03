#!/usr/bin/env python3
"""Build a material inventory for a decompiled WeChat mini program.

Usage:
  python inventory.py --root /path/to/miniapp
  python inventory.py --root /path/to/miniapp --output inventory.json --strict

Supports two layouts:
  - source or developer-tools export: app.json + per-page js/wxml
  - raw wxapkg unpack: app-config.json + app-service.js + per-page html

The script does not execute target code. It reads the configuration and checks
declared pages, subpackages and plugins against the files on disk.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_config(root: Path) -> tuple[dict | None, str | None, str | None]:
    for name in ("app.json", "app-config.json"):
        path = root / name
        if not path.is_file():
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8")), name, None
        except json.JSONDecodeError as exc:
            return None, name, f"{name} is not valid JSON: {exc}"
    return None, None, "app.json or app-config.json not found"


def check_page(root: Path, page: str, raw_mode: bool) -> dict:
    base = root / page
    present = {
        "js": base.with_suffix(".js").is_file(),
        "wxml": base.with_suffix(".wxml").is_file(),
        "html": base.with_suffix(".html").is_file(),
        "json": base.with_suffix(".json").is_file(),
        "wxss": base.with_suffix(".wxss").is_file(),
    }
    complete = present["html"] if raw_mode else (present["js"] and present["wxml"])
    return {
        "page": page,
        "present": present,
        "complete": complete,
    }


def build_inventory(root: Path) -> dict:
    config, config_name, error = load_config(root)
    result = {
        "root": str(root.resolve()),
        "material_type": "unknown",
        "config_file": config_name,
        "app_id": None,
        "app_service": (root / "app-service.js").is_file(),
        "page_frame": (root / "page-frame.js").is_file(),
        "pages": [],
        "subpackages": [],
        "plugins": [],
        "permissions": {},
        "completeness": "blocked",
        "limitations": [],
    }
    if error:
        result["limitations"].append(error)
        return result

    raw_mode = config_name == "app-config.json"
    result["material_type"] = "wxapkg_unpacked" if raw_mode else "source"

    result["app_id"] = config.get("appId") or config.get("appid")
    project_config = root / "project.config.json"
    if project_config.is_file():
        try:
            project_data = json.loads(project_config.read_text(encoding="utf-8"))
            result["app_id"] = (
                result["app_id"]
                or project_data.get("appid")
                or project_data.get("appId")
            )
        except json.JSONDecodeError:
            result["limitations"].append("project.config.json is not valid JSON")

    if raw_mode and not result["app_service"]:
        result["limitations"].append("app-service.js not found")

    pages = config.get("pages") or []
    page_results = [check_page(root, page, raw_mode) for page in pages]
    result["pages"] = page_results
    missing_pages = [item["page"] for item in page_results if not item["complete"]]
    if missing_pages:
        result["limitations"].append(
            f"{len(missing_pages)} page(s) missing required files"
        )

    subpackages = config.get("subPackages") or config.get("subpackages") or []
    for sub in subpackages:
        sub_root = sub.get("root")
        if not sub_root:
            result["limitations"].append("subpackage without root")
            continue
        sub_dir = root / sub_root
        sub_pages = sub.get("pages") or []
        page_checks = [check_page(sub_dir, page, raw_mode) for page in sub_pages]
        complete = sub_dir.is_dir() and (
            not sub_pages or all(item["complete"] for item in page_checks)
        )
        result["subpackages"].append(
            {
                "root": sub_root,
                "exists": sub_dir.is_dir(),
                "pages": page_checks,
                "complete": complete,
            }
        )
        if not sub_dir.is_dir():
            result["limitations"].append(f"subpackage directory missing: {sub_root}")

    plugins = config.get("plugins") or {}
    for name, meta in plugins.items():
        result["plugins"].append(
            {
                "name": name,
                "version": meta.get("version"),
                "provider": meta.get("provider"),
                "external": True,
            }
        )

    result["permissions"] = {
        "permission": config.get("permission") or {},
        "requiredPrivateInfos": config.get("requiredPrivateInfos") or [],
    }

    sub_ok = all(item["complete"] for item in result["subpackages"])
    pages_ok = not missing_pages
    entry_ok = result["app_service"] if raw_mode else (root / "app.js").is_file()
    if pages_ok and sub_ok and entry_ok and not error:
        result["completeness"] = "complete"
    elif pages_ok or result["subpackages"]:
        result["completeness"] = "partial"
    else:
        result["completeness"] = "blocked"

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a mini program material inventory")
    parser.add_argument("--root", required=True, help="decompiled mini program root")
    parser.add_argument("--output", help="write JSON to this path instead of stdout")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when completeness is not 'complete'",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2

    result = build_inventory(root)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    if args.strict and result["completeness"] != "complete":
        print(
            f"error: completeness is {result['completeness']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
