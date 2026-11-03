#!/usr/bin/env python3
"""Validate a coverage matrix against the audit quality gate.

Usage:
  python check_coverage.py --coverage coverage.json

Input may be a JSON array or an object with an "assets" array. Each item
requires a type and a status. Partial and not-tested items require a reason.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STATUS = {"tested", "partial", "not_tested"}


def load(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: coverage file is not valid JSON: {exc}")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("assets"), list):
        return data["assets"]
    raise SystemExit('error: expected a JSON array or an object with an "assets" array')


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a coverage matrix")
    parser.add_argument("--coverage", required=True, help="coverage JSON file")
    parser.add_argument("--output", help="write the check result to this path")
    args = parser.parse_args()

    assets = load(Path(args.coverage))
    errors: list[str] = []
    counts = {status: 0 for status in STATUS}

    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            errors.append(f"asset[{index}]: expected object")
            continue
        asset_type = asset.get("type")
        status = str(asset.get("status", "")).lower()
        if not asset_type:
            errors.append(f"asset[{index}]: missing type")
        if status not in STATUS:
            errors.append(
                f"asset[{index}]: invalid status '{asset.get('status')}'"
            )
            continue
        counts[status] += 1
        if status in {"partial", "not_tested"} and not asset.get("reason"):
            errors.append(
                f"asset[{index}] ({asset_type}): {status} requires a reason"
            )

    result = {
        "assets": len(assets),
        **counts,
        "errors": errors,
        "passed": not errors,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
