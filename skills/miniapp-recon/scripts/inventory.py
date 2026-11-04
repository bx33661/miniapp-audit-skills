#!/usr/bin/env python3
"""Build a material inventory for a decompiled WeChat mini program.

Usage:
  python inventory.py --root /path/to/miniapp
  python inventory.py --root /path/to/miniapp --output inventory.json --strict

Supports two layouts:
  - source or developer-tools export: app.json + per-page js/wxml
  - raw wxapkg unpack: app-config.json + app-service.js + per-page html

The output follows assets/material-check-output.schema.json.
The script does not execute target code.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

APPID_RE = re.compile(r"wx[0-9a-f]{16}")


def infer_app_id(root: Path) -> str | None:
    for part in [root.name, *[parent.name for parent in root.parents]]:
        match = APPID_RE.search(part)
        if match:
            return match.group(0)
    return None


def load_config(root: Path) -> tuple[dict | None, str | None, str | None]:
    for name in ("app.json", "app-config.json"):
        path = root / name
        if not path.is_file():
            continue
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                return None, name, f"{name} must contain a JSON object"
            return config, name, None
        except json.JSONDecodeError as exc:
            return None, name, f"{name} is not valid JSON: {exc}"
    return None, None, "app.json or app-config.json not found"


def check_page(root: Path, page: str, raw_mode: bool) -> dict:
    base = root / page
    present = {
        suffix: Path(str(base) + "." + suffix).is_file()
        for suffix in ("js", "wxml", "html", "json", "wxss")
    }
    complete = present["html"] if raw_mode else (present["js"] and present["wxml"])
    return {"page": page, "present": present, "complete": complete}


def build_inventory(root: Path, app_id_override: str | None = None) -> dict:
    config, config_name, error = load_config(root)
    raw_mode = config_name == "app-config.json"
    scanned_at = datetime.now(timezone.utc).isoformat()
    result = {
        "skill": "miniapp-recon",
        "scanned_at": scanned_at,
        "input_path": str(root.resolve()),
        "material_type": "unknown",
        "completeness": "BLOCKED",
        "metadata": {
            "app_id": app_id_override or infer_app_id(root),
            "pages_count": None,
            "subpackages_count": None,
            "plugins_count": None,
        },
        "main_package": {"status": "UNKNOWN", "issues": []},
        "subpackages": {"declared": [], "found": [], "missing": [], "issues": []},
        "plugins": {"declared": [], "issues": []},
        "quality": {
            "version_consistency": "UNKNOWN",
            "decompile_quality": "UNKNOWN",
            "issues": [],
        },
        "next_actions": [],
        "coverage_notes": [
            "Version consistency and decompiled code quality have not been assessed.",
        ],
        "config_file": config_name,
        "app_service": (root / "app-service.js").is_file(),
        "page_frame": (root / "page-frame.js").is_file(),
        "pages": [],
        "permissions": {},
    }
    if error:
        result["coverage_notes"].append(error)
        result["next_actions"].append("provide app.json or app-config.json")
        return result

    result["material_type"] = "decompiled_source"
    result["app_id"] = app_id_override or config.get("appId") or config.get("appid")
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
            result["coverage_notes"].append("project.config.json is not valid JSON")

    result["app_id"] = result["app_id"] or infer_app_id(root)
    result["metadata"]["app_id"] = result["app_id"]
    if config.get("appName"):
        result["metadata"]["app_name"] = config["appName"]

    pages = config.get("pages") or []
    page_results = [check_page(root, page, raw_mode) for page in pages]
    result["pages"] = page_results
    result["metadata"]["pages_count"] = len(page_results)

    main_issues = []
    for item in page_results:
        if item["complete"]:
            continue
        if raw_mode:
            main_issues.append(
                {
                    "type": "missing_page_js",
                    "file": item["page"],
                    "impact": "page html missing in raw wxapkg layout",
                }
            )
        else:
            if not item["present"]["js"]:
                main_issues.append(
                    {
                        "type": "missing_page_js",
                        "file": item["page"],
                        "impact": "page logic is missing",
                    }
                )
            if not item["present"]["wxml"]:
                main_issues.append(
                    {
                        "type": "missing_page_wxml",
                        "file": item["page"],
                        "impact": "page template is missing",
                    }
                )
    result["main_package"] = {
        "status": "ISSUES" if main_issues else "OK",
        "issues": main_issues,
    }
    if main_issues:
        result["coverage_notes"].append(
            f"{len(main_issues)} page issue(s) detected"
        )

    if raw_mode and not result["app_service"]:
        result["coverage_notes"].append("app-service.js not found")

    subpackages = config.get("subPackages") or config.get("subpackages") or []
    declared = []
    found = []
    missing = []
    sub_issues = []
    for sub in subpackages:
        sub_root = sub.get("root")
        if not sub_root:
            sub_issues.append(
                {
                    "type": "missing_subpackage",
                    "subpackage": "unknown",
                    "impact": "subpackage declaration without root",
                }
            )
            continue
        declared.append(sub_root)
        sub_dir = root / sub_root
        if sub_dir.is_dir():
            found.append(sub_root)
        else:
            missing.append(sub_root)
            sub_issues.append(
                {
                    "type": "missing_subpackage",
                    "subpackage": sub_root,
                    "impact": "declared subpackage is not present in the captured material",
                }
            )
        sub_pages = sub.get("pages") or []
        if not sub_pages:
            sub_issues.append(
                {
                    "type": "missing_subpackage_page",
                    "subpackage": sub_root,
                    "impact": "no declared pages available to verify this subpackage",
                }
            )
        for page in sub_pages:
            item = check_page(root, str(Path(sub_root) / page), raw_mode)
            result["pages"].append(item)
            if not item["complete"]:
                sub_issues.append(
                    {
                        "type": "missing_subpackage_page",
                        "subpackage": sub_root,
                        "file": item["page"],
                        "impact": (
                            "page html missing in raw wxapkg layout"
                            if raw_mode else "page logic or template is missing"
                        ),
                    }
                )
    result["subpackages"] = {
        "declared": declared,
        "found": found,
        "missing": missing,
        "issues": sub_issues,
    }
    result["metadata"]["subpackages_count"] = len(declared)
    result["metadata"]["pages_count"] = len(result["pages"])
    if missing:
        result["coverage_notes"].append(
            "missing subpackages: " + ", ".join(missing)
        )

    plugins = dict(config.get("plugins") or {})
    for sub in subpackages:
        for name, declaration in (sub.get("plugins") or {}).items():
            plugins[f"{sub.get('root', 'unknown')}:{name}"] = declaration
    plugin_issues = []
    for name, declaration in plugins.items():
        provider = declaration.get("provider") if isinstance(declaration, dict) else None
        local_dir = root / "__plugin__" / provider if provider else None
        present = local_dir is not None and local_dir.is_dir()
        plugin_issues.append(
            {
                "type": "unverified_plugin" if present else "missing_plugin",
                "plugin": name,
                "provider": provider or "unknown",
                "impact": (
                    "local plugin directory found; version and completeness are unverified"
                    if present else "declared plugin material was not found or cannot be located"
                ),
            }
        )
    result["plugins"] = {"declared": list(plugins.keys()), "issues": plugin_issues}
    result["metadata"]["plugins_count"] = len(plugins)
    if plugin_issues:
        result["coverage_notes"].append(
            "Declared plugins require independent verification of captured code and version."
        )

    result["permissions"] = {
        "declared": list((config.get("permission") or {}).keys()),
        "required_private_infos": config.get("requiredPrivateInfos") or [],
    }

    entry_ok = result["app_service"] if raw_mode else (root / "app.js").is_file()
    if not entry_ok:
        result["coverage_notes"].append("entry file not found")
        result["main_package"]["status"] = "ISSUES"
        result["main_package"]["issues"].append(
            {
                "type": "missing_entry",
                "file": "app-service.js" if raw_mode else "app.js",
                "impact": "application entry logic is missing",
            }
        )

    if main_issues or sub_issues or plugin_issues or not entry_ok:
        result["completeness"] = "PARTIAL"
        result["next_actions"].extend(
            [
                "provide missing material and verify declared plugin code and versions",
                "re-run inventory after adding the material",
            ]
        )
    else:
        result["completeness"] = "COMPLETE"
        result["next_actions"].append("proceed to threat modeling")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a mini program material inventory")
    parser.add_argument("--root", required=True, help="decompiled mini program root")
    parser.add_argument("--app-id", help="known mini program appid")
    parser.add_argument("--output", help="write JSON to this path instead of stdout")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when completeness is not 'COMPLETE'",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2

    result = build_inventory(root, args.app_id)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    if args.strict and result["completeness"] != "COMPLETE":
        print(
            f"error: completeness is {result['completeness']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
