#!/usr/bin/env python3
"""Build a material inventory for a decompiled WeChat mini program.

Usage:
  python inventory.py --root /path/to/miniapp
  python inventory.py --root /path/to/miniapp --output inventory.json --strict

The script does not execute target code. It reads app.json and checks the
declared pages, subpackages and plugins against the files on disk.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_app_json(root: Path) -> tuple[dict | None, str | None]:
    path = root / "app.json"
    if not path.is_file():
        return None, "app.json not found"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"app.json is not valid JSON: {exc}"


def check_page(root: Path, page: str) -> dict:
    base = root / page
    present = {
        "js": base.with_suffix(".js").is_file(),
        "wxml": base.with_suffix(".wxml").is_file(),
        "json": base.with_suffix(".json").is_file(),
        "wxss": base.with_suffix(".wxss").is_file(),
    }
    return {
        "page": page,
        "present": present,
        "complete": present["js"] and present["wxml"],
    }


def build_inventory(root: Path) -> dict:
    app, error = load_app_json(root)
    result = {
        "root": str(root.resolve()),
        "app_json": app is not None,
        "app_id": None,
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

    result["app_id"] = app.get("appId") or app.get("appid")
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
    pages = app.get("pages") or []
    page_results = [check_page(root, page) for page in pages]
    result["pages"] = page_results
    missing_pages = [item["page"] for item in page_results if not item["complete"]]
    if missing_pages:
        result["limitations"].append(
            f"{len(missing_pages)} page(s) missing js or wxml"
        )

    subpackages = app.get("subPackages") or app.get("subpackages") or []
    for sub in subpackages:
        sub_root = sub.get("root")
        sub_pages = sub.get("pages") or []
        if not sub_root:
            result["limitations"].append("subpackage without root")
            continue
        sub_dir = root / sub_root
        page_checks = [check_page(sub_dir, page) for page in sub_pages]
        result["subpackages"].append(
            {
                "root": sub_root,
                "exists": sub_dir.is_dir(),
                "pages": page_checks,
                "complete": sub_dir.is_dir()
                and all(item["complete"] for item in page_checks),
            }
        )
        if not sub_dir.is_dir():
            result["limitations"].append(f"subpackage directory missing: {sub_root}")

    plugins = app.get("plugins") or {}
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
        "permission": app.get("permission") or {},
        "requiredPrivateInfos": app.get("requiredPrivateInfos") or [],
    }

    sub_ok = all(item["complete"] for item in result["subpackages"])
    pages_ok = not missing_pages
    if pages_ok and sub_ok and not error:
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
